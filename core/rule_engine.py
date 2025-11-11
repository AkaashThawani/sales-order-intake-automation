from models import SessionLocal, WorkflowRule, Order
from typing import Dict, List, Any
import json

class RuleEngine:
    """Business rule engine for automated order processing"""

    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        self._rules_loaded = False

    def _ensure_rules_loaded(self):
        """Ensure default rules are loaded (lazy loading)"""
        if not self._rules_loaded:
            self._load_default_rules()
            self._rules_loaded = True

    def _load_default_rules(self):
        """Load default business rules if they don't exist"""
        default_rules = [
            {
                "name": "large_quantity_approval",
                "description": "Orders with total quantity > 50 require approval",
                "conditions": {"field": "total_quantity", "operator": ">", "value": 50},
                "actions": {"action": "require_approval", "message": "Large quantity order requires manager approval"},
                "priority": 1,
                "rule_type": "quantity"
            },
            {
                "name": "bulk_discount_eligible",
                "description": "Orders with quantity > 20 are eligible for bulk discount",
                "conditions": {"field": "total_quantity", "operator": ">", "value": 20},
                "actions": {"action": "add_note", "message": "Eligible for bulk discount - contact sales"},
                "priority": 2,
                "rule_type": "quantity"
            },
            {
                "name": "small_order_check",
                "description": "Orders with quantity < 3 may need follow-up",
                "conditions": {"field": "total_quantity", "operator": "<", "value": 3},
                "actions": {"action": "add_note", "message": "Small order - consider upsell opportunities"},
                "priority": 3,
                "rule_type": "quantity"
            },
            {
                "name": "high_value_review",
                "description": "High value orders need review",
                "conditions": {"field": "total_amount", "operator": ">", "value": 1000},
                "actions": {"action": "require_approval", "message": "High value order requires review"},
                "priority": 1,
                "rule_type": "amount"
            }
        ]

        # Create default rules if they don't exist
        for rule_data in default_rules:
            existing = self.db.query(WorkflowRule).filter(WorkflowRule.name == rule_data["name"]).first()
            if not existing:
                rule = WorkflowRule(**rule_data)
                self.db.add(rule)

        self.db.commit()

    def evaluate_order(self, order: Order) -> Dict[str, Any]:
        """Evaluate all active rules against an order"""

        # Ensure rules are loaded
        self._ensure_rules_loaded()

        rules = self.db.query(WorkflowRule).filter(
            WorkflowRule.is_active == True
        ).order_by(WorkflowRule.priority).all()

        applied_rules = []
        actions_taken = []

        # Calculate order metrics for rule evaluation
        metrics = self._calculate_order_metrics(order)

        for rule in rules:
            if self._rule_matches(metrics, rule.conditions):
                action_result = self._apply_action(order, rule.actions)
                applied_rules.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "action": action_result
                })
                actions_taken.append(action_result)

        return {
            "applied_rules": applied_rules,
            "actions_taken": actions_taken,
            "requires_approval": any("require_approval" in action for action in actions_taken)
        }

    def _calculate_order_metrics(self, order: Order) -> Dict[str, Any]:
        """Calculate metrics for rule evaluation"""
        # Get line items
        line_items = order.line_items or []

        total_quantity = sum(item.requested_quantity for item in line_items)

        # Calculate total amount (simplified - would need product pricing)
        total_amount = 0.0  # Placeholder - would calculate from product prices

        return {
            "total_quantity": total_quantity,
            "total_amount": total_amount,
            "item_count": len(line_items),
            "customer_email": order.customer.email if order.customer else None
        }

    def _rule_matches(self, metrics: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Check if rule conditions match order metrics"""

        field = conditions.get("field")
        operator = conditions.get("operator")
        value = conditions.get("value")

        if field not in metrics:
            return False

        actual_value = metrics[field]

        # Handle different operators
        if operator == ">":
            return actual_value > value
        elif operator == ">=":
            return actual_value >= value
        elif operator == "<":
            return actual_value < value
        elif operator == "<=":
            return actual_value <= value
        elif operator == "==":
            return actual_value == value
        elif operator == "!=":
            return actual_value != value
        elif operator == "between" and isinstance(value, list) and len(value) == 2:
            return value[0] <= actual_value <= value[1]
        elif operator == "in" and isinstance(value, list):
            return actual_value in value
        elif operator == "contains":
            return str(value).lower() in str(actual_value).lower()

        return False

    def _apply_action(self, order: Order, actions: Dict[str, Any]) -> str:
        """Apply rule action to order"""

        action_type = actions.get("action")
        message = actions.get("message", "")

        if action_type == "require_approval":
            order.approval_required = True
            return f"require_approval: {message}"

        elif action_type == "add_note":
            current_notes = order.customer_notes or ""
            order.customer_notes = current_notes + f"\n\nRule Note: {message}"
            return f"add_note: {message}"

        elif action_type == "set_priority":
            priority_level = actions.get("value", "normal")
            # Could add priority field to order if needed
            return f"set_priority_{priority_level}: {message}"

        elif action_type == "apply_discount":
            discount_pct = actions.get("value", 0)
            # Could implement discount logic here
            return f"apply_discount_{discount_pct}%: {message}"

        elif action_type == "flag_for_review":
            order.requires_human_review = True
            return f"flag_for_review: {message}"

        return f"unknown_action: {message}"

    def create_rule(self, name: str, conditions: Dict[str, Any], actions: Dict[str, Any],
                   description: str = "", priority: int = 1, rule_type: str = "quantity") -> int:
        """Create a new business rule"""

        # Validate rule doesn't already exist
        existing = self.db.query(WorkflowRule).filter(WorkflowRule.name == name).first()
        if existing:
            raise ValueError(f"Rule with name '{name}' already exists")

        # Validate conditions
        required_condition_fields = ["field", "operator", "value"]
        if not all(field in conditions for field in required_condition_fields):
            raise ValueError(f"Conditions must include: {required_condition_fields}")

        # Validate actions
        if "action" not in actions:
            raise ValueError("Actions must include 'action' field")

        rule = WorkflowRule(
            name=name,
            description=description,
            conditions=conditions,
            actions=actions,
            priority=priority,
            rule_type=rule_type,
            is_active=True
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        return rule.id

    def get_active_rules(self) -> List[Dict[str, Any]]:
        """Get all active rules"""
        rules = self.db.query(WorkflowRule).filter(WorkflowRule.is_active == True).order_by(WorkflowRule.priority).all()

        return [{
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "conditions": rule.conditions,
            "actions": rule.actions,
            "priority": rule.priority,
            "rule_type": rule.rule_type,
            "created_at": rule.created_at.isoformat() if rule.created_at else None
        } for rule in rules]

    def update_rule(self, rule_id: int, updates: Dict[str, Any]) -> bool:
        """Update an existing rule"""
        rule = self.db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
        if not rule:
            return False

        # Update allowed fields
        allowed_fields = ["name", "description", "conditions", "actions", "priority", "is_active"]
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(rule, field, value)

        self.db.commit()
        return True

    def deactivate_rule(self, rule_id: int) -> bool:
        """Deactivate a rule (soft delete)"""
        rule = self.db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
        if not rule:
            return False

        rule.is_active = False
        self.db.commit()
        return True

    def test_rule(self, conditions: Dict[str, Any], test_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Test a rule against sample metrics (without DB operations)"""

        matches = self._rule_matches(test_metrics, conditions)

        # Simulate action application
        mock_order = type('MockOrder', (), {'customer_notes': '', 'approval_required': False})()
        action_result = self._apply_action(mock_order, {"action": "test", "message": "Test action"})

        return {
            "rule_matches": matches,
            "test_metrics": test_metrics,
            "conditions": conditions,
            "simulated_action": action_result,
            "would_require_approval": mock_order.approval_required
        }

    def get_rules_by_type(self, rule_type: str) -> List[Dict[str, Any]]:
        """Get rules filtered by type"""
        rules = self.db.query(WorkflowRule).filter(
            WorkflowRule.is_active == True,
            WorkflowRule.rule_type == rule_type
        ).order_by(WorkflowRule.priority).all()

        return [{
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "conditions": rule.conditions,
            "actions": rule.actions,
            "priority": rule.priority
        } for rule in rules]

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about rule usage"""
        total_rules = self.db.query(WorkflowRule).count()
        active_rules = self.db.query(WorkflowRule).filter(WorkflowRule.is_active == True).count()

        # Count rules by type
        rule_types = {}
        type_counts = self.db.query(WorkflowRule.rule_type, WorkflowRule.is_active).all()
        for rule_type, is_active in type_counts:
            if is_active:
                rule_types[rule_type] = rule_types.get(rule_type, 0) + 1

        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": total_rules - active_rules,
            "rules_by_type": rule_types
        }
