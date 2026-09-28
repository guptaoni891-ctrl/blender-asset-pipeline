"""Operators for previewing and explicitly applying asset fixes."""

from collections import Counter

import bpy
from bpy.props import IntProperty

from ..fixing.execution import execute_fix_actions
from ..fixing.models import FixExecutionStatus, FixPlan, FixRisk
from ..fixing.planner import missing_object_action, plan_fixes
from ..fixing.reporting import format_fix_report
from ..preferences import get_preferences
from ..ui.fix_state import action_from_state, clear_fix_plan, store_fix_plan
from ..ui.state import store_reports
from ..utils.blender_adapter import snapshot_object
from ..utils.fixing_adapter import snapshot_fix_target
from ..validation import format_reports, validate_asset


class BAP_OT_generate_fix_plan(bpy.types.Operator):
    """Generate a preview for the objects in the latest validation run."""

    bl_idname = "bap.generate_fix_plan"
    bl_label = "Generate Fix Plan"
    bl_description = "Preview fixes for the objects from the latest validation"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Require a completed validation with at least one target."""
        state = getattr(context.scene, "bap_validation_state", None)
        return bool(state and state.has_run and state.targets)

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Build a fresh plan without changing any Blender data."""
        config = get_preferences(context).to_validation_config()
        validation_state = context.scene.bap_validation_state
        pairs = []
        fresh_objects = []
        fresh_reports = []
        missing_actions = []
        objects_by_key = {}

        for reference in list(validation_state.targets):
            obj = reference.target
            if obj is None:
                missing_actions.append(
                    missing_object_action(reference.object_key, reference.object_name)
                )
                continue
            target = snapshot_fix_target(obj)
            report = validate_asset(target.asset, config)
            pairs.append((target, report))
            fresh_objects.append(obj)
            fresh_reports.append(report)
            objects_by_key[target.object_key] = obj

        plan = plan_fixes(
            pairs,
            config,
            (obj.name for obj in bpy.data.objects),
        )
        if missing_actions:
            plan = FixPlan((*plan.actions, *missing_actions))
        store_reports(validation_state, fresh_reports, fresh_objects)
        store_fix_plan(context.scene.bap_fix_state, plan, objects_by_key)

        supported = sum(action.supported for action in plan.actions)
        unsupported = len(plan.actions) - supported
        self.report(
            {"INFO"},
            f"Previewed {len(plan.actions)} fix(es): "
            f"{supported} supported, {unsupported} manual/unsupported",
        )
        return {"FINISHED"}


class BAP_OT_select_all_safe_fixes(bpy.types.Operator):
    """Select every supported SAFE action in the preview."""

    bl_idname = "bap.select_all_safe_fixes"
    bl_label = "Select All Safe"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Select supported safe actions and leave higher risks unchanged."""
        for action in context.scene.bap_fix_state.actions:
            if action.supported and action.risk == FixRisk.SAFE.value:
                action.selected = True
        return {"FINISHED"}


class BAP_OT_deselect_all_fixes(bpy.types.Operator):
    """Deselect every action in the preview."""

    bl_idname = "bap.deselect_all_fixes"
    bl_label = "Deselect All"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Clear all action selections."""
        for action in context.scene.bap_fix_state.actions:
            action.selected = False
        return {"FINISHED"}


class BAP_OT_clear_fix_plan(bpy.types.Operator):
    """Discard the current preview without applying it."""

    bl_idname = "bap.clear_fix_plan"
    bl_label = "Clear Fix Plan"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Clear transient fix state."""
        clear_fix_plan(context.scene.bap_fix_state)
        return {"FINISHED"}


class BAP_OT_apply_selected_fixes(bpy.types.Operator):
    """Apply only explicitly selected, supported preview actions."""

    bl_idname = "bap.apply_selected_fixes"
    bl_label = "Apply Selected Fixes"
    bl_description = "Confirm and apply only the selected fixes"
    bl_options = {"REGISTER", "UNDO"}

    object_count: IntProperty(options={"SKIP_SAVE"})
    fix_count: IntProperty(options={"SKIP_SAVE"})
    safe_count: IntProperty(options={"SKIP_SAVE"})
    caution_count: IntProperty(options={"SKIP_SAVE"})
    destructive_count: IntProperty(options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Require a plan containing at least one selected supported action."""
        state = getattr(context.scene, "bap_fix_state", None)
        return bool(
            state
            and state.has_plan
            and any(action.selected and action.supported for action in state.actions)
        )

    def _selected_items(self, context: bpy.types.Context) -> list[object]:
        return [
            action
            for action in context.scene.bap_fix_state.actions
            if action.selected and action.supported
        ]

    def invoke(
        self,
        context: bpy.types.Context,
        _event: bpy.types.Event,
    ) -> set[str]:
        """Show an explicit risk summary before any asset modification."""
        items = self._selected_items(context)
        if not items:
            self.report({"WARNING"}, "No supported fixes are selected")
            return {"CANCELLED"}
        counts = Counter(item.risk for item in items)
        self.object_count = len({item.object_key for item in items})
        self.fix_count = len(items)
        self.safe_count = counts[FixRisk.SAFE.value]
        self.caution_count = counts[FixRisk.CAUTION.value]
        self.destructive_count = counts[FixRisk.DESTRUCTIVE.value]
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, _context: bpy.types.Context) -> None:
        """Draw the confirmation summary."""
        layout = self.layout
        layout.label(text="This will modify Blender data.", icon="ERROR")
        layout.label(text=f"Objects affected: {self.object_count}")
        layout.label(text=f"Selected fixes: {self.fix_count}")
        row = layout.row(align=True)
        row.label(text=f"SAFE {self.safe_count}", icon="CHECKMARK")
        row.label(text=f"CAUTION {self.caution_count}", icon="ERROR")
        row.label(text=f"DESTRUCTIVE {self.destructive_count}", icon="CANCEL")
        layout.label(text="One Undo step will revert this apply operation.")

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Apply selected actions, report outcomes, then revalidate targets."""
        state = context.scene.bap_fix_state
        selected_items = self._selected_items(context)
        if not selected_items:
            self.report({"WARNING"}, "No supported fixes are selected")
            return {"CANCELLED"}

        actions = [action_from_state(item) for item in selected_items]
        objects_by_key = {item.object_key: item.target for item in selected_items}
        report = execute_fix_actions(context, actions, objects_by_key)
        print(format_fix_report(report))

        attempted_objects = []
        seen_pointers = set()
        for item in selected_items:
            obj = item.target
            if obj is None or obj.as_pointer() in seen_pointers:
                continue
            seen_pointers.add(obj.as_pointer())
            attempted_objects.append(obj)

        if attempted_objects:
            config = get_preferences(context).to_validation_config()
            validation_reports = [
                validate_asset(snapshot_object(obj), config)
                for obj in attempted_objects
            ]
            store_reports(
                context.scene.bap_validation_state,
                validation_reports,
                attempted_objects,
            )
            print("\nVALIDATION AFTER FIXES\n")
            print(format_reports(validation_reports))

        statuses = Counter(result.status for result in report.results)
        clear_fix_plan(state)
        applied = statuses[FixExecutionStatus.APPLIED]
        failed = statuses[FixExecutionStatus.FAILED]
        stale = statuses[FixExecutionStatus.STALE]
        severity = "WARNING" if failed or stale or report.context_warnings else "INFO"
        self.report(
            {severity},
            f"Applied {applied} fix(es); {failed} failed, {stale} stale",
        )
        return {"FINISHED"}
