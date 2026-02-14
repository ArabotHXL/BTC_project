from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional


@dataclass
class SkillSpec:
    id: str
    name: str
    name_zh: str
    desc: str
    desc_zh: str
    required_permissions: List[str]
    input_schema: Dict[str, Any]
    output_fields: List[str]
    run_fn: Optional[Callable] = None
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)

    def validate_input(self, payload: dict) -> List[str]:
        errors = []
        schema = self.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field_name in required:
            if field_name not in payload:
                errors.append(f"Missing required field: {field_name}")

        type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
        for field_name, field_spec in properties.items():
            if field_name in payload:
                expected_type = field_spec.get("type")
                if expected_type and expected_type in type_map:
                    if not isinstance(payload[field_name], type_map[expected_type]):
                        errors.append(f"Field '{field_name}' must be {expected_type}, got {type(payload[field_name]).__name__}")

        return errors

    def apply_defaults(self, payload: dict) -> dict:
        result = dict(payload)
        for field_name, field_spec in self.input_schema.get("properties", {}).items():
            if field_name not in result and "default" in field_spec:
                result[field_name] = field_spec["default"]
        return result

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_zh": self.name_zh,
            "desc": self.desc,
            "desc_zh": self.desc_zh,
            "required_permissions": self.required_permissions,
            "input_schema": self.input_schema,
            "output_fields": self.output_fields,
            "version": self.version,
            "tags": self.tags,
        }
