import logging
from typing import Dict, Optional, List
from skills.spec import SkillSpec

logger = logging.getLogger(__name__)


class SkillRegistry:
    _instance = None
    _skills: Dict[str, SkillSpec] = {}

    @classmethod
    def instance(cls) -> 'SkillRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, spec: SkillSpec):
        if spec.id in self._skills:
            logger.warning(f"Skill '{spec.id}' already registered, overwriting")
        if spec.run_fn is None:
            raise ValueError(f"Skill '{spec.id}' must have a run_fn")
        self._skills[spec.id] = spec
        logger.info(f"Skill registered: {spec.id}")

    def get(self, skill_id: str) -> Optional[SkillSpec]:
        return self._skills.get(skill_id)

    def list_all(self) -> List[SkillSpec]:
        return list(self._skills.values())

    def list_for_permissions(self, user_permissions: List[str]) -> List[SkillSpec]:
        """Return only skills the user has run permission for"""
        result = []
        for spec in self._skills.values():
            if any(p in user_permissions for p in spec.required_permissions):
                result.append(spec)
        return result

    def is_registered(self, skill_id: str) -> bool:
        return skill_id in self._skills

    @property
    def count(self) -> int:
        return len(self._skills)
