import logging

from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

def load_all_skills():
    registry = SkillRegistry.instance()
    skill_modules = [
        'skills.impl.telemetry_snapshot',
        'skills.impl.alert_triage',
        'skills.impl.rca_quick_diagnose',
        'skills.impl.ticket_draft',
        'skills.impl.curtailment_dry_run',
    ]
    
    loaded = 0
    for module_path in skill_modules:
        try:
            import importlib
            module = importlib.import_module(module_path)
            spec = getattr(module, 'spec', None)
            if spec:
                registry.register(spec)
                loaded += 1
            else:
                logger.warning(f"No 'spec' found in {module_path}")
        except Exception as e:
            logger.error(f"Failed to load skill from {module_path}: {e}")
    
    logger.info(f"Skills loaded: {loaded}/{len(skill_modules)} (registry total: {registry.count})")
    return loaded
