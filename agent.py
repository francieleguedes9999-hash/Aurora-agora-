import json
from .model import Model
from .local_model import LocalModelManager
from .research import Researcher
from .diagnostics import DiagnosticTool
from .tools.fs import Workspace, FileTools
from .tools.terminal import SafeTerminal
from .tools.test_runner import TestRunner
from .memory_store import LongTermMemory
from .context import ProjectContext
from .context_intelligence import ContextIntelligence
from .planner import AdaptivePlanner
from .session_store import SessionStore
from .task_manager import TaskManager
from .development_cycle import DevelopmentCycle
from .patcher import PatchEngine
from .app_factory import AppFactory
from .assets import AssetManager
from .project_manager import ProjectManager
from .autonomous import AutonomousDeveloper
from typing import Any
from .app_builder import AppBuilder
from .app_spec import DetailedSpecBuilder
from .visual_editor import VisualEditor
from .workflow_engine import WorkflowEngine
from .visual_workflow import VisualWorkflow
from .deploy import DeployManager
from .studio import AuroraStudio
from .artifacts import ArtifactManager
from .versions import ProjectVersionManager
from .releases import ReleaseManager
from .release_intelligence import ReleaseIntelligence
from .orchestrator import AuroraOrchestrator
from .knowledge_graph import KnowledgeGraph
from .impact import ImpactPlanner
from .change_intelligence import ChangeIntelligence
from .regression_intelligence import RegressionIntelligence
from .autonomous_engineering import AutonomousEngineering
from .regression_engineering import RegressionEngineeringCoordinator
from .repair_learning import RepairLearning
from .predictive_engineering import PredictiveEngineering
from .preventive_engineering import PreventiveEngineering
from .engineering_guardrails import EngineeringGuardrails
from .adaptive_guardrails import AdaptiveGuardrails
from .self_healing_guardrails import SelfHealingGuardrails
from .engineering_recovery_planner import EngineeringRecoveryPlanner
from .recovery_execution import RecoveryExecutionEngine
from .task_decomposer import TaskDecomposer
from .task_execution import TaskExecutionCoordinator
from .scheduler import ParallelScheduler
from .execution_monitor import ExecutionMonitor
from .resource_intelligence import ResourceIntelligence
from .brain import CognitiveBrain, BrainConfig
from .brain_learning import BrainToolLearning
from .brain_meta_reasoning import MetaReasoning
from .adaptive_cognitive_cycle import AdaptiveCognitiveCycle
from .training_lab import TrainingLab
from .research_planner import ResearchPlanner
from .research_execution import ResearchExecution
from .project_blueprint import ProjectBlueprint
from .project_orchestrator import ProjectOrchestrator
from .app_evolution import AppEvolution
from .local_access import LocalAccess
from .local_execution import LocalExecutionRuntime
from .local_preview import LocalPreview
from .visual_contract import VisualContract
from .code_repair import CodeRepair
from .app_build_coordinator import AppBuildCoordinator
from .question_generator import QuestionGenerator
from .api_server import AuroraAPI
from .media_engine import MediaEngine
from .multimodal_router import MultimodalRouter
from .question_generator import QuestionGenerator
from .api_server import AuroraAPI

class Agent:
    def __init__(self, workspace='workspace', model=None, researcher=None, max_steps=8):
        self.model = model or Model()
        self.local_models = LocalModelManager()
        self._prepare_local_model()
        self.researcher = researcher or Researcher()
        self.workspace = Workspace(workspace)
        self.local_access = LocalAccess(self.workspace.root)
        self.tools = FileTools(self.workspace, self.researcher)
        self.terminal = SafeTerminal(self.workspace.root)
        self.local_execution = LocalExecutionRuntime(self.workspace.root, self.terminal)
        self.local_preview = LocalPreview(self.workspace.root, self.local_execution)
        self.visual_contract = VisualContract(self.workspace.root)
        self.visual_contract.agent = self
        self.test_runner = TestRunner(self.workspace.root)
        self.diagnostics = DiagnosticTool()
        self.memory = LongTermMemory(self.workspace.root)
        self.context = ProjectContext(self.workspace.root)
        self.context_intelligence = ContextIntelligence(self)
        self.planner = AdaptivePlanner(self.workspace.root)
        self.sessions = SessionStore(self.workspace.root)
        self.tasks = TaskManager(self.workspace.root)
        self.patcher = PatchEngine(self.workspace.root)
        self.code_repair = CodeRepair(self.workspace.root, self.patcher)
        self.app_factory = AppFactory(self.workspace.root)
        self.app_builder = AppBuilder(self.workspace.root, self.test_runner)
        self.app_build_coordinator = AppBuildCoordinator(self)
        self.question_generator = QuestionGenerator(self.model)
        self.api = AuroraAPI(self, self.workspace.root)
        self.media = MediaEngine(self.workspace.root)
        self.multimodal_router = MultimodalRouter(self)
        self.question_generator = QuestionGenerator(self.model)
        self.api = AuroraAPI(self, self.workspace.root)
        self.app_spec = DetailedSpecBuilder(self.workspace.root)
        self.visual_editor = VisualEditor(self.workspace.root)
        self.workflows = WorkflowEngine(self.workspace.root)
        self.visual_workflows = VisualWorkflow(self.workspace.root)
        self.deployments = DeployManager(self.workspace.root)
        self.artifacts = ArtifactManager(self.workspace.root)
        self.versions = ProjectVersionManager(self.workspace.root)
        self.releases = ReleaseManager(self.workspace.root)
        self.studio = AuroraStudio(self)
        self.release_intelligence = ReleaseIntelligence(self)
        self.orchestrator = AuroraOrchestrator(self)
        self.knowledge_graph = KnowledgeGraph(self.workspace.root)
        self.impact = ImpactPlanner(self.workspace.root, self.knowledge_graph)
        self.change_intelligence = ChangeIntelligence(self.workspace.root, self.impact, self.knowledge_graph)
        self.regression_intelligence = RegressionIntelligence(self.workspace.root, self.change_intelligence, self.test_runner)
        self.engineering = AutonomousEngineering(self)
        self.regression_engineering = RegressionEngineeringCoordinator(self)
        self.repair_learning = RepairLearning(self.workspace.root)
        self.predictive_engineering = PredictiveEngineering(self.workspace.root, self.impact, self.knowledge_graph, self.repair_learning)
        self.preventive_engineering = PreventiveEngineering(self)
        self.engineering_guardrails = EngineeringGuardrails(self)
        self.adaptive_guardrails = AdaptiveGuardrails(self)
        self.self_healing_guardrails = SelfHealingGuardrails(self)
        self.engineering_recovery_planner = EngineeringRecoveryPlanner(self)
        self.recovery_execution = RecoveryExecutionEngine(self)
        self.task_decomposer = TaskDecomposer(self.workspace.root)
        self.task_execution = TaskExecutionCoordinator(self.workspace.root, self.task_decomposer, self.tasks)
        self.scheduler = ParallelScheduler(self.workspace.root, self.tasks, self.tasks.max_workers)
        self.resources = ResourceIntelligence(self.workspace.root)
        self.execution_monitor = ExecutionMonitor(self.workspace.root)
        self.assets = AssetManager(self.workspace.root)
        self.projects = ProjectManager(self.workspace.root)
        self.cycle = DevelopmentCycle(self, max_steps=max_steps)
        self.autonomous = AutonomousDeveloper(self)
        self.max_steps = max_steps
        self.training_lab = TrainingLab(str(self.workspace.root / ".aurora" / "training_lab"))
        self.research_planner = ResearchPlanner(self)
        self.research_execution = ResearchExecution(self)
        self.project_blueprint = ProjectBlueprint(self)
        self.project_orchestrator = ProjectOrchestrator(self)
        self.app_evolution = AppEvolution(self)
        self.brain = CognitiveBrain(self, self.model, BrainConfig())
        self.adaptive_cognitive_cycle = AdaptiveCognitiveCycle(self.brain)

    def select_local_model_for_task(self, task: str) -> dict[str, Any]:
        """Choose an installed local model for a task without downloading anything."""
        result = self.local_models.select_for_task(task)
        selected = result.get('selected')
        if result.get('ok') and selected:
            self.model.local_model = selected
        return result

    def _prepare_local_model(self):
        """Synchronize the local model boundary without downloading anything."""
        provider = getattr(self.model, 'provider', 'auto')
        if provider not in {'auto', 'local', 'ollama'}:
            return
        try:
            status = self.local_models.status()
            if not status.get('ok'):
                return
            configured = getattr(self.model, 'local_model', None)
            names = [m.get('name') for m in status.get('models', []) if isinstance(m, dict) and m.get('name')]
            if configured and configured in names:
                return
            if configured and any(n and n.split(':')[0] == configured.split(':')[0] for n in names):
                return
            if names and not configured:
                self.model.local_model = names[0]
                if not getattr(self.model, 'model', None):
                    self.model.model = names[0]
        except Exception:
            # Model preparation must never prevent Aurora from starting.
            return

    def available_tools(self):
        return ['list_files','read_file','write_file','edit_file','preview_edit','rollback_edit','research','run_command','run_tests','diagnose','remember','recall','plan','resume_plan','project_context','app_factory','build_app','assets','visual_edit','workflow','visual_workflow','session','projects','tasks','parallel_tasks','autonomous','engineering','deploy','artifacts','versions','studio','release_intelligence','knowledge_graph','impact','change_intelligence','regression_intelligence','repair_learning','predictive_engineering','preventive_engineering','engineering_guardrails','adaptive_guardrails','self_healing_guardrails','engineering_recovery_planner','recovery_execution','brain_memory','brain_meta_reasoning','predictive_cognitive_recovery','adaptive_cognitive_cycle','training_lab','research_plan','code_repair','regression_engineering','research_execution','project_blueprint','project_orchestrator','app_evolution','decompose','scheduler','resources','monitor','brain_learning','local_access','local_execution','local_preview','visual_contract','app_build_coordinator','questions','api','media','multimodal','local_models']

    def _call(self, tool, args):
        if tool in {'list_files','read_file','write_file','research'}:
            return self.tools.call(tool, args)
        if tool == 'edit_file':
            return self.patcher.apply(args['path'], args.get('old', ''), args.get('new', ''), args.get('expected_sha256'))
        if tool == 'preview_edit':
            return self.patcher.preview(args['path'], args.get('old', ''), args.get('new', ''))
        if tool == 'rollback_edit':
            return self.patcher.rollback_last()
        if tool == 'run_command':
            return self.terminal.run(args['command'], args.get('cwd'))
        if tool == 'run_tests':
            return self.test_runner.run()
        if tool == 'diagnose':
            return self.diagnostics.call(args['result'])
        if tool == 'remember':
            m = self.memory.remember(args['text'], args.get('kind','fact'), args.get('tags',[]), args.get('metadata',{}))
            return {'ok': True, 'memory': m.__dict__}
        if tool == 'recall':
            return {'ok': True, 'memories': [m.__dict__ for m in self.memory.search(args.get('query',''), args.get('limit',8))]}
        if tool == 'plan':
            plan = self.planner.replace(args.get('request', ''), args.get('steps', []))
            return {'ok': True, 'plan': self.planner.context()}
        if tool == 'resume_plan':
            plan = self.planner.resume()
            return {'ok': True, 'plan': self.planner.context()}
        if tool == 'project_context':
            return {'ok': True, 'context': self.context.format(args.get('query', ''), args.get('limit', 6), args.get('max_total_chars', 7000))}
        if tool == 'brain_memory':
            return self.brain.persistence.status() if self.brain.persistence else {'ok': False, 'enabled': False}
        if tool == 'brain_meta_reasoning':
            return self.brain.meta.status() if self.brain.meta else {'ok': False, 'enabled': False}
        if tool == 'adaptive_cognitive_cycle':
            action = args.get('action', 'status')
            if action == 'run':
                return self.adaptive_cognitive_cycle.run(
                    args.get('request', ''),
                    session_id=args.get('session_id'),
                    max_steps=args.get('max_steps'),
                    inputs=args.get('inputs'),
                    research=bool(args.get('research', True)),
                    recovery=bool(args.get('recovery', True)),
                    confirmed=bool(args.get('confirmed', False)),
                    max_recovery_attempts=int(args.get('max_recovery_attempts', 1)),
                )
            return self.adaptive_cognitive_cycle.status()
        if tool == 'predictive_cognitive_recovery':
            return self.brain.predictive_recovery.status() if self.brain.predictive_recovery else {'ok': False, 'enabled': False}
        if tool == 'local_access':
            return self.local_access.status()
        if tool == 'local_execution':
            action=args.get('action','status')
            if action == 'run': return self.local_execution.run(args.get('command',''), args.get('cwd'), args.get('timeout'))
            if action == 'start': return self.local_execution.start(args.get('command',''), args.get('cwd'), args.get('name','app'), args.get('host','127.0.0.1'))
            if action == 'stop': return self.local_execution.stop(args.get('name','app'))
            return self.local_execution.status()
        if tool == 'visual_contract':
            action=args.get('action','status')
            if action == 'compare':
                spec=args.get('spec') or (self.project_blueprint.load() or {}).get('spec') or {}
                inspected=args.get('inspected') or self.local_preview.inspect(args['app_path'])
                return self.visual_contract.compare(args['app_path'], spec, inspected)
            if action == 'correction_plan': return self.visual_contract.correction_plan(args.get('comparison'))
            if action == 'apply_correction': return self.visual_contract.apply_correction(args['app_path'], args.get('comparison'))
            if action == 'auto_correct':
                spec = args.get('spec') or (self.project_blueprint.load() or {}).get('spec') or {}
                return self.visual_contract.auto_correct(args['app_path'], spec, max_rounds=args.get('max_rounds', 3))
            return self.visual_contract.status()
        if tool == 'regression_engineering':
            action = args.get('action', 'status')
            if action == 'run':
                return self.regression_engineering.run(args.get('request', ''), session_id=args.get('session_id'), research=bool(args.get('research', False)), max_steps=args.get('max_steps'), max_attempts=args.get('max_attempts'), limit=args.get('limit', 50))
            return self.regression_engineering.status()
        if tool == 'code_repair':
            action = args.get('action', 'status')
            if action == 'inspect': return self.code_repair.inspect(args['path'])
            if action == 'plan': return self.code_repair.plan_from_diagnosis(args.get('diagnosis'))
            if action == 'repair':
                return self.code_repair.repair(args['path'], args.get('old', ''), args.get('new', ''), args.get('expected_sha256'), bool(args.get('validate', True)))
            return self.code_repair.status()
        if tool == 'local_preview':
            action=args.get('action','status')
            if action == 'build': return self.local_preview.build(args['app_path'])
            if action == 'serve': return self.local_preview.serve(args['app_path'], args.get('port'), args.get('name','preview'))
            if action == 'inspect': return self.local_preview.inspect(args['app_path'])
            if action == 'stop': return self.local_preview.stop(args.get('name','preview'))
            return self.local_preview.status()
        if tool == 'brain_learning':
            action = args.get('action', 'status')
            if action == 'suggest':
                return {'ok': True, 'strategies': self.brain.learning.suggest(args.get('request', ''), args.get('limit', 5))}
            return self.brain.learning.status()
        if tool == 'project_orchestrator':
            action = args.get('action', 'status')
            if action == 'prepare':
                return self.project_orchestrator.prepare(args.get('request', ''), bool(args.get('research', True)))
            if action == 'run':
                return self.project_orchestrator.run(args.get('max_rounds', 20), args.get('requested_workers'))
            if action == 'resume':
                return self.project_orchestrator.resume(args.get('max_rounds', 20), args.get('requested_workers'))
            return self.project_orchestrator.status()
        if tool == 'app_evolution':
            action = args.get('action', 'status')
            if action == 'prepare':
                spec = args.get('spec') or (self.project_blueprint.load() or {}).get('spec') or {}
                return self.app_evolution.prepare(spec, args.get('blueprint_id', ''))
            if action == 'prompt':
                return self.app_evolution.prompt(args.get('module_id', ''))
            if action == 'mark':
                return self.app_evolution.mark(args.get('module_id', ''), args.get('status', 'done'), args.get('result'))
            if action == 'validate':
                return self.app_evolution.validate(args.get('module_id', ''))
            if action == 'affected_modules':
                return self.app_evolution.affected_modules(args.get('comparison', {}))
            if action == 'regression_plan':
                return self.app_evolution.regression_plan(args.get('comparison', {}), args.get('limit', 50))
            return self.app_evolution.status()
        if tool == 'project_blueprint':
            action = args.get('action', 'status')
            if action == 'build':
                return self.project_blueprint.build(args.get('request', ''), bool(args.get('research', True)))
            return self.project_blueprint.status()
        if tool == 'research_execution':
            action = args.get('action', 'run')
            if action == 'run':
                return self.research_execution.run(
                    args.get('request', ''), session_id=args.get('session_id'),
                    max_stages=int(args.get('max_stages', 5)), max_retries=int(args.get('max_retries', 1)),
                    research=bool(args.get('research', True)), plan=args.get('plan'))
            return self.research_execution.status()
        if tool == 'research_plan':
            action = args.get('action', 'build')
            if action == 'build':
                context = self.context_intelligence.build(args.get('request', ''), args.get('session_id'), True, limit=8, max_chars=12000, reuse=True, stage='planning')
                return self.research_planner.build(args.get('request', ''), context=context)
            return self.research_planner.status()
        if tool == 'training_lab':
            action = args.get('action', 'status')
            if action == 'add':
                return {'ok': True, 'item': self.training_lab.add(args.get('kind', 'text'), args.get('title', 'material'), args.get('content', ''), source=args.get('source', ''), tags=args.get('tags', []), metadata=args.get('metadata', {}), path=args.get('path', ''), transcript=args.get('transcript', ''), license=args.get('license', ''))}
            if action == 'add_file':
                return {'ok': True, 'item': self.training_lab.add_file(args['path'], kind=args.get('kind'), title=args.get('title'), tags=args.get('tags', []), transcript=args.get('transcript', ''), license=args.get('license', ''))}
            if action == 'add_article_url':
                return {'ok': True, 'item': self.training_lab.add_article_url(args['url'], title=args.get('title'), tags=args.get('tags', []), license=args.get('license', ''))}
            if action == 'search':
                return {'ok': True, 'items': self.training_lab.search(args.get('query', ''), args.get('limit', 8))}
            if action == 'context':
                return {'ok': True, 'context': self.training_lab.context(args.get('query', ''), args.get('limit', 5), args.get('max_chars', 8000))}
            if action == 'export':
                return {'ok': True, 'path': self.training_lab.export_dataset(args.get('name', 'aurora_training'))}
            if action == 'list':
                return {'ok': True, 'items': self.training_lab.list(args.get('kind'), args.get('tag'))}
            return self.training_lab.status()
        if tool == 'preventive_engineering':
            action = args.get('action', 'status')
            if action == 'preflight':
                return self.preventive_engineering.preflight(args.get('target', ''), args.get('depth', 2), args.get('limit', 50))
            if action == 'run':
                request = args.get('request', '')
                def _runner():
                    return self.cycle.run(request, session_id=args.get('session_id'))
                return self.preventive_engineering.run(request, _runner, session_id=args.get('session_id'), depth=args.get('depth', 2), limit=args.get('limit', 50), run_preventive_tests=bool(args.get('run_preventive_tests', True)), confirmed=bool(args.get('confirmed', False)))
            return self.preventive_engineering.status()
        if tool == 'engineering_guardrails':
            action = args.get('action', 'status')
            if action in {'preflight', 'evaluate'}:
                return self.engineering_guardrails.evaluate(
                    args.get('target', ''),
                    confirmed=bool(args.get('confirmed', False)),
                    require_confirmation_for=tuple(args.get('require_confirmation_for', ['high'])),
                    max_files_without_confirmation=int(args.get('max_files_without_confirmation', 25)),
                )
            return self.engineering_guardrails.status()
        if tool == 'adaptive_guardrails':
            action = args.get('action', 'status')
            if action in {'preflight', 'evaluate', 'policy'}:
                if action == 'policy':
                    return self.adaptive_guardrails.policy(args.get('target', ''))
                return self.adaptive_guardrails.evaluate(args.get('target', ''), confirmed=bool(args.get('confirmed', False)))
            return self.adaptive_guardrails.status()
        if tool == 'self_healing_guardrails':
            action = args.get('action', 'status')
            if action == 'run':
                request = args.get('request', '')
                def _runner():
                    return self.cycle.run(request, session_id=args.get('session_id'))
                return self.self_healing_guardrails.run(
                    request, _runner, confirmed=bool(args.get('confirmed', False)),
                    max_recovery_attempts=int(args.get('max_recovery_attempts', 1))
                )
            if action == 'alternatives':
                guard = self.adaptive_guardrails.evaluate(args.get('target', ''), confirmed=bool(args.get('confirmed', False)))
                return {'ok': True, 'alternatives': self.self_healing_guardrails.alternatives(args.get('target', ''), guard), 'guardrails': guard}
            return self.self_healing_guardrails.status()
        if tool == 'engineering_recovery_planner':
            action = args.get('action', 'status')
            if action in {'plan', 'preflight'}:
                return self.engineering_recovery_planner.plan(
                    args.get('target', ''), failure=args.get('failure', ''),
                    diagnosis=args.get('diagnosis'), depth=args.get('depth', 2),
                    limit=args.get('limit', 50), max_options=args.get('max_options', 8),
                    confirmed=bool(args.get('confirmed', False)))
            if action == 'alternatives':
                return self.engineering_recovery_planner.alternatives(
                    args.get('target', ''), failure=args.get('failure', ''),
                    diagnosis=args.get('diagnosis'), depth=args.get('depth', 2),
                    limit=args.get('limit', 50), max_options=args.get('max_options', 8),
                    confirmed=bool(args.get('confirmed', False)))
            return self.engineering_recovery_planner.status()
        if tool == 'recovery_execution':
            action = args.get('action', 'status')
            if action == 'run':
                return self.recovery_execution.run(
                    args.get('request', ''), failure=args.get('failure', ''),
                    diagnosis=args.get('diagnosis'), session_id=args.get('session_id'),
                    confirmed=bool(args.get('confirmed', False)),
                    timeout=args.get('timeout'), retries=args.get('retries', 0),
                    max_attempts=args.get('max_attempts'), research=bool(args.get('research', False)),
                    max_steps=args.get('max_steps'), test_timeout=args.get('test_timeout'))
            return self.recovery_execution.status()
        if tool == 'predictive_engineering':
            action = args.get('action', 'status')
            if action == 'predict':
                return self.predictive_engineering.predict(args.get('target', ''), args.get('depth', 2), args.get('limit', 50))
            if action == 'preflight':
                return self.predictive_engineering.preflight(args.get('target', ''), args.get('depth', 2), args.get('limit', 50))
            return self.predictive_engineering.status()
        if tool == 'repair_learning':
            action = args.get('action', 'status')
            if action == 'record':
                return {'ok': True, 'case': self.repair_learning.record(args.get('failure', ''), args.get('diagnosis'), args.get('repair', ''), args.get('target'), bool(args.get('success', False)), args.get('metadata', {}))}
            if action == 'similar':
                return {'ok': True, 'cases': self.repair_learning.similar(args.get('failure', ''), args.get('diagnosis'), args.get('target'), args.get('limit', 5))}
            if action == 'patterns':
                return {'ok': True, 'patterns': self.repair_learning.patterns(args.get('limit', 10))}
            if action == 'contextual':
                return self.repair_learning.contextual(args.get('failure', ''), args.get('diagnosis'), args.get('target'), args.get('limit', 5))
            return self.repair_learning.status()
        if tool == 'engineering':
            action = args.get('action', 'status')
            if action == 'run':
                return self.engineering.run(args.get('request', ''), session_id=args.get('session_id'), research=bool(args.get('research', False)), max_steps=args.get('max_steps'), max_attempts=args.get('max_attempts'))
            if action == 'run_resilient':
                return self.regression_engineering.run(args.get('request', ''), session_id=args.get('session_id'), research=bool(args.get('research', False)), max_steps=args.get('max_steps'), max_attempts=args.get('max_attempts'), limit=args.get('limit', 50))
            if action == 'resume':
                return self.engineering.resume(args.get('request'), session_id=args.get('session_id'), research=bool(args.get('research', False)), max_steps=args.get('max_steps'), max_attempts=args.get('max_attempts'))
            return self.engineering.status()
        if tool == 'resources':
            action = args.get('action', 'status')
            if action == 'inspect': return self.resources.inspect(args.get('path'))
            if action == 'check': return self.resources.check(args.get('requirements', {}))
            if action == 'port': return self.resources.check_port(args.get('port'), args.get('host', '127.0.0.1'))
            if action == 'workers': return self.resources.recommend_workers(args.get('requested'), args.get('tasks', []))
            return self.resources.status()
        if tool == 'monitor':
            action = args.get('action', 'status')
            if action == 'cancel':
                return self.execution_monitor.cancel()
            if action == 'command':
                return self.execution_monitor.run_command(self.terminal, args.get('command', ''), args.get('cwd'), timeout=args.get('timeout'), retries=args.get('retries', 0))
            return self.execution_monitor.status()
        if tool == 'scheduler':
            action = args.get('action', 'status')
            if action == 'plan': return self.scheduler.plan()
            if action == 'adaptive_plan': return self.scheduler.adaptive_plan(args.get('requested_workers'))
            if action == 'run':
                def runner(task):
                    if task.kind != 'command':
                        return {'ok': False, 'error': f'kind não suportado: {task.kind}'}
                    command = task.payload.get('command')
                    if not command: return {'ok': False, 'error': 'command ausente'}
                    return self.terminal.run(command, task.payload.get('cwd'))
                return self.scheduler.run(runner, args.get('max_rounds', 20))
            if action == 'adaptive_run':
                def adaptive_runner(task):
                    if task.kind != 'command':
                        return {'ok': False, 'error': f'kind não suportado: {task.kind}'}
                    command = task.payload.get('command')
                    if not command: return {'ok': False, 'error': 'command ausente'}
                    return self.terminal.run(command, task.payload.get('cwd'))
                return self.scheduler.run_adaptive(adaptive_runner, args.get('max_rounds', 20), args.get('requested_workers'))
            if action == 'monitored_run':
                def monitored_runner(task):
                    if task.kind != 'command':
                        return {'ok': False, 'error': f'kind não suportado: {task.kind}'}
                    command = task.payload.get('command')
                    if not command: return {'ok': False, 'error': 'command ausente'}
                    return self.terminal.run(command, task.payload.get('cwd'), timeout=task.payload.get('command_timeout'))
                return self.scheduler.run_monitored(monitored_runner, args.get('max_rounds', 20), args.get('timeout'), args.get('retries', 0), args.get('retry_delay', 0.0), args.get('requested_workers'), adaptive=bool(args.get('adaptive', True)))
            return self.scheduler.status()
        if tool == 'decompose':
            action = args.get('action', 'status')
            if action == 'create':
                return self.task_decomposer.decompose(args.get('request', ''), bool(args.get('reuse', True)), bool(args.get('replace', False)))
            if action == 'next':
                return self.task_decomposer.next_ready()
            if action == 'mark':
                return self.task_decomposer.mark(args.get('task_id', ''), args.get('status', 'done'), args.get('note', ''))
            if action == 'prepare':
                return self.task_execution.prepare(args.get('request', ''), bool(args.get('reuse', True)), bool(args.get('replace', False)))
            if action in {'execute', 'resume'}:
                def runner(task):
                    result = self.engineering.run(task.title, max_steps=args.get('max_steps', self.max_steps), max_attempts=args.get('max_attempts', 2))
                    return result
                return self.task_execution.run(runner, args.get('max_rounds', 20))
            if action == 'execution_status':
                return self.task_execution.status()
            return self.task_decomposer.status()
        if tool == 'change_intelligence':
            action = args.get('action', 'status')
            if action == 'plan':
                return self.change_intelligence.plan(args.get('target', ''), args.get('depth', 2), args.get('limit', 50))
            if action == 'compare':
                return self.change_intelligence.compare(args.get('before', {}), args.get('after', {}), args.get('planned', {}))
            return self.change_intelligence.status()
        if tool == 'regression_intelligence':
            action = args.get('action', 'status')
            if action == 'select':
                return self.regression_intelligence.select(args.get('planned', {}), args.get('comparison', {}), args.get('limit', 50))
            if action == 'validate':
                return self.regression_intelligence.validate(args.get('planned', {}), args.get('comparison', {}), limit=args.get('limit', 50))
            return self.regression_intelligence.status()
        if tool == 'impact':
            action=args.get('action','status')
            if action == 'analyze':
                return self.impact.analyze(args.get('target',''), args.get('depth',2), args.get('limit',50))
            if action == 'preflight':
                return self.impact.preflight(args.get('target',''), args.get('depth',2))
            return self.impact.status()
        if tool == 'knowledge_graph':
            action=args.get('action','status')
            if action == 'build': return self.knowledge_graph.build(bool(args.get('force',False)))
            if action == 'query': return self.knowledge_graph.query(args.get('term',''), args.get('limit',20))
            if action == 'impact': return self.knowledge_graph.impact(args.get('target',''), args.get('depth',2), args.get('limit',50))
            if action == 'graph': return self.knowledge_graph.graph(bool(args.get('rebuild',False)))
            return self.knowledge_graph.status()
        if tool == 'context_intelligence':
            action = args.get('action', 'build')
            if action == 'build':
                return self.context_intelligence.build(args.get('request', ''), args.get('session_id'), bool(args.get('research', False)), args.get('limit', 6), args.get('max_chars', 12000), bool(args.get('reuse', True)), args.get('stage', 'planning'))
            if action == 'stage_packet':
                return self.context_intelligence.stage_packet(args.get('request', ''), args.get('stage', 'planning'), session_id=args.get('session_id'), research=bool(args.get('research', False)), limit=args.get('limit', 6), max_chars=args.get('max_chars'), reuse=bool(args.get('reuse', True)))
            return self.context_intelligence.status()
        if tool == 'questions':
            action = args.get('action', 'generate')
            if action == 'generate':
                return self.question_generator.generate(args.get('topic',''), args.get('count',5), args.get('difficulty','medium'), args.get('type','multiple_choice'), args.get('context',''))
            return {'ok': True, 'service': 'questions'}
        if tool == 'local_models':
            action = args.get('action', 'status')
            if action == 'list': return self.local_models.list_models()
            if action == 'pull': return self.local_models.pull(args.get('model', ''))
            if action == 'runtime': return self.local_models.runtime()
            return self.local_models.status()
        if tool == 'multimodal':
            action = args.get('action', 'status')
            if action == 'run':
                return self.multimodal_router.run(args.get('request',''), **args.get('options', {}))
            if action == 'classify':
                return self.multimodal_router.classify(args.get('request',''))
            return self.multimodal_router.status()
        if tool == 'media':
            action = args.get('action', 'status')
            if action == 'generate':
                return self.media.generate(args.get('kind','image'), args.get('prompt',''), args.get('provider','local_artifact'), **args.get('options', {}))
            if action == 'configure_http':
                return self.media.configure_http_provider(args.get('name','remote'), args.get('config', {}))
            return self.media.status()
        if tool == 'api':
            action = args.get('action', 'status')
            if action == 'create_key': return self.api.create_key(args.get('name','app'))
            if action == 'revoke_key': return self.api.revoke_key(args.get('key',''))
            if action == 'serve':
                server = self.api.serve(args.get('host','127.0.0.1'), args.get('port',8787))
                return {'ok': True, 'host': args.get('host','127.0.0.1'), 'port': int(args.get('port',8787)), 'message': 'Servidor pronto; execute server.serve_forever() no processo que o hospeda.'}
            return self.api.status()
        if tool == 'questions':
            action=args.get('action','generate')
            if action == 'generate': return self.question_generator.generate(args.get('topic',''), args.get('count',5), args.get('difficulty','medium'), args.get('type','multiple_choice'), args.get('context',''))
            return {'ok':True,'service':'questions'}
        if tool == 'api':
            action=args.get('action','status')
            if action == 'create_key': return self.api.create_key(args.get('name','app'))
            if action == 'revoke_key': return self.api.revoke_key(args.get('key',''))
            if action == 'serve':
                self.api.serve(args.get('host','127.0.0.1'), args.get('port',8787))
                return {'ok':True,'host':args.get('host','127.0.0.1'),'port':int(args.get('port',8787))}
            return self.api.status()
        if tool == 'app_build_coordinator':
            action = args.get('action', 'status')
            if action == 'create_app':
                return self.app_build_coordinator.create_app(
                    args.get('description', ''), args.get('name'),
                    bool(args.get('research', False)), bool(args.get('run_tests', True))
                )
            if action == 'build_and_validate':
                return self.app_build_coordinator.build_and_validate(args.get('description', ''), args.get('name'), bool(args.get('run_tests', True)))
            if action == 'repair_cycle':
                return self.app_build_coordinator.repair_cycle(
                    args.get('description', ''), args.get('name'), bool(args.get('run_tests', True)),
                    args.get('patches'), args.get('max_attempts', 3), args.get('app_path')
                )
            return self.app_build_coordinator.status()
        if tool == 'build_app':
            action = args.get('action', 'build')
            if action == 'specification':
                return self.app_builder.specification(args.get('description', ''), args.get('name'))
            if action == 'preview':
                return self.app_builder.preview(args.get('description', ''), args.get('name'))
            return self.app_builder.build(args.get('description', ''), args.get('name'), args.get('run_tests', True))
        if tool == 'app_factory':
            action = args.get('action', 'preview')
            payload = {k: args[k] for k in ('name','kind','frontend','backend','database','auth','description') if k in args}
            return self.app_factory.create(**payload) if action == 'create' else self.app_factory.preview(**payload)
        if tool == 'visual_edit':
            action=args.get('action','apply')
            if action=='preview': return self.visual_editor.preview(args['app_path'], args.get('instruction',''))
            if action=='undo': return self.visual_editor.undo(args['app_path'])
            if action=='redo': return self.visual_editor.redo(args['app_path'])
            if action=='inspect_component': return self.visual_editor.inspect_component(args['app_path'], args['component_id'])
            if action in {'set_properties','preview_properties'}:
                return self.visual_editor.set_properties(args['app_path'], args['component_id'], args.get('properties', {}), preview=(action=='preview_properties'))
            return self.visual_editor.apply(args['app_path'], args.get('instruction',''))
        if tool == 'visual_workflow':
            op = args.get('op', 'get')
            wid = args.get('workflow_id')
            if op == 'from_workflow':
                workflow = self.workflows.get(wid)
                if not workflow.get('ok'): return workflow
                graph = self.visual_workflows.from_workflow(workflow['workflow'])
                return self.visual_workflows.save(wid, graph)
            if op == 'save': return self.visual_workflows.save(wid, args.get('graph', {}))
            if op == 'update_node': return self.visual_workflows.update_node(wid, args['node_id'], args.get('properties', {}))
            if op == 'html': return {'ok': True, 'html': self.visual_workflows.to_html(wid)}
            return self.visual_workflows.get(wid)
        if tool == 'workflow':
            action = args.get('action', 'list')
            if action == 'validate':
                return self.workflows.validate(args.get('workflow', {}))
            if action == 'create':
                return self.workflows.create(args.get('workflow', {}))
            if action == 'get':
                return self.workflows.get(args['workflow_id'])
            if action == 'status':
                return self.workflows.status(args.get('run_id'))
            if action == 'run':
                workflow_id = args['workflow_id']
                def dispatch(name, payload, context):
                    if name == 'set':
                        key = payload.get('key'); value = payload.get('value')
                        if not key: raise ValueError('set requer key')
                        context[key] = value
                        return value
                    result = self._call(name, payload)
                    return result
                return self.workflows.run(workflow_id, dispatch, args.get('context', {}), args.get('max_steps', 100))
            return {'ok': True, 'workflows': self.workflows.list()}
        if tool == 'versions':
            action=args.get('action','status')
            if action == 'snapshot': return self.versions.snapshot(args.get('label','snapshot'))
            if action == 'list': return self.versions.list()
            if action == 'history': return self.versions.history(args.get('limit',20))
            if action == 'diff': return self.versions.diff(args['version_id'], args.get('against','current'))
            if action == 'restore': return self.versions.restore(args['version_id'], args.get('target'), bool(args.get('allow_workspace',False)))
            return self.versions.status()
        if tool == 'artifacts':
            action=args.get('action','status')
            if action == 'build': return self.artifacts.build(args.get('label','build'), args.get('include_manifest',True))
            if action == 'verify': return self.artifacts.verify(args.get('artifact_id'))
            if action == 'restore': return self.artifacts.restore(args['artifact_id'], args.get('destination'))
            if action == 'list': return self.artifacts.list()
            return self.artifacts.status()
        if tool == 'studio':
            action = args.get('action', 'status')
            if action == 'run':
                return self.studio.run(args.get('request', ''), deploy_config=args.get('deploy_config'), session_id=args.get('session_id'), max_steps=args.get('max_steps', self.max_steps), deploy=bool(args.get('deploy', False)), dry_run=bool(args.get('dry_run', False)))
            if action == 'resume':
                return self.studio.resume(args.get('request'), deploy_config=args.get('deploy_config'), session_id=args.get('session_id'), max_steps=args.get('max_steps', self.max_steps), deploy=bool(args.get('deploy', False)), dry_run=bool(args.get('dry_run', False)))
            return self.studio.status()
        if tool == 'orchestrator':
            action = args.get('action', 'status')
            if action == 'plan':
                return self.orchestrator.plan(args.get('request',''), bool(args.get('deploy',False)), bool(args.get('dry_run',False)), bool(args.get('verify',False)))
            if action == 'run':
                return self.orchestrator.run(args.get('request',''), bool(args.get('deploy',False)), bool(args.get('dry_run',False)), bool(args.get('verify',False)), args.get('label','orchestrated-release'), args.get('deploy_config'), args.get('session_id'), args.get('max_steps', self.max_steps), bool(args.get('force',False)))
            if action == 'resume':
                return self.orchestrator.resume(args.get('request'), deploy=bool(args.get('deploy',False)), dry_run=bool(args.get('dry_run',False)), verify=bool(args.get('verify',False)), label=args.get('label','orchestrated-release'), deploy_config=args.get('deploy_config'), session_id=args.get('session_id'), max_steps=args.get('max_steps', self.max_steps), force=bool(args.get('force',False)))
            return self.orchestrator.status()
        if tool == 'release_intelligence':
            action = args.get('action', 'status')
            if action == 'plan': return self.release_intelligence.plan(args.get('label','release'), bool(args.get('deploy',False)), bool(args.get('verify',False)))
            if action == 'run': return self.release_intelligence.run(args.get('request',''), args.get('label','release'), args.get('deploy_config'), bool(args.get('deploy',False)), bool(args.get('dry_run',False)), bool(args.get('verify',False)), args.get('session_id'), args.get('max_steps', self.max_steps))
            return self.release_intelligence.status()
        if tool == 'releases':
            action = args.get('action', 'status')
            if action == 'plan': return self.releases.plan(args.get('label','release'), bool(args.get('snapshot',True)), bool(args.get('artifact',True)))
            if action == 'create': return self.releases.create(args.get('label','release'), bool(args.get('snapshot',True)), bool(args.get('artifact',True)))
            if action == 'deploy': return self.releases.deploy(args.get('release_id'), args.get('config',{}), bool(args.get('dry_run',False)))
            if action == 'verify': return self.releases.verify(args.get('release_id'), args.get('config',{}))
            if action == 'rollback': return self.releases.rollback(args.get('release_id'), args.get('target_release_id'), args.get('config',{}))
            if action == 'list': return self.releases.list()
            if action == 'history': return self.releases.history(args.get('limit',20))
            return self.releases.status()
        if tool == 'deploy':
            action = args.get('action', 'status')
            config = args.get('config', args)
            if action == 'validate': return self.deployments.validate(config)
            if action == 'plan': return self.deployments.plan(config)
            if action in {'dry_run', 'deploy'}: return self.deployments.deploy(config, args.get('package_path'), dry_run=(action == 'dry_run'))
            if action == 'verify': return self.deployments.verify(config)
            if action == 'rollback': return self.deployments.rollback(config)
            return self.deployments.status()
        if tool == 'assets':
            action = args.get('action', 'list')
            if action == 'icon':
                return self.assets.icon(args['name'], args.get('label'), args.get('size', 128))
            if action == 'storyboard':
                return self.assets.storyboard(args['name'], args.get('scenes', []))
            return {'ok': True, 'assets': self.assets.list()}
        if tool == 'session':
            return {'ok': True, 'sessions': self.sessions.list()}
        if tool == 'projects':
            action = args.get('action', 'list')
            if action == 'create':
                project = self.projects.create(args['name'], args.get('description', ''))
                return {'ok': True, 'project': project.__dict__}
            if action == 'register':
                project = self.projects.register(args['name'], args['path'], args.get('description', ''))
                return {'ok': True, 'project': project.__dict__}
            if action == 'activate':
                project = self.projects.activate(args['project_id'])
                return {'ok': True, 'project': project.__dict__}
            if action == 'remove':
                project = self.projects.remove(args['project_id'], bool(args.get('delete_files', False)))
                return {'ok': True, 'project': project.__dict__}
            return {'ok': True, **self.projects.summary()}
        if tool == 'autonomous':
            action = args.get('action', 'run')
            if action == 'status':
                return self.autonomous.status()
            if action == 'resume':
                return self.autonomous.resume(args.get('request'), args.get('session_id'))
            return self.autonomous.run(args.get('request', ''), args.get('session_id'))
        if tool == 'tasks':
            if args.get('action') == 'status':
                return {'ok': True, **self.tasks.status()}
            if args.get('action') == 'retry_failed':
                return {'ok': True, 'tasks': [t.__dict__ for t in self.tasks.retry_failed()]}
            items = args.get('tasks', [])
            return {'ok': True, 'tasks': [t.__dict__ for t in self.tasks.create_many(items)]}
        if tool == 'parallel_tasks':
            items = args.get('tasks', [])
            if items:
                self.tasks.create_many(items)
            def runner(task):
                if task.kind != 'command':
                    return {'ok': False, 'error': f"kind não suportado: {task.kind}"}
                command = task.payload.get('command')
                if not command:
                    return {'ok': False, 'error': 'command ausente'}
                return self.terminal.run(command, task.payload.get('cwd'))
            self.tasks.run_ready(runner, args.get('max_workers'))
            return {'ok': True, **self.tasks.status()}
        raise ValueError(f'ferramenta desconhecida: {tool}')

    def run_brain(self, request, session_id=None, max_steps=None, inputs=None):
        return self.brain.run(request, session_id=session_id, max_steps=max_steps, inputs=inputs)

    def run_adaptive_brain(self, request, session_id=None, max_steps=None, inputs=None):
        return self.adaptive_cognitive_cycle.run(request, session_id=session_id, max_steps=max_steps, inputs=inputs)

    def brain_status(self):
        return self.brain.status()

    def run_cycle(self, request, session_id=None):
        return self.cycle.run(request, session_id=session_id)

    def resume_cycle(self, request=None, session_id=None):
        return self.cycle.resume(request, session_id=session_id)

    def run_autonomous(self, request, session_id=None):
        return self.autonomous.run(request, session_id=session_id)

    def resume_autonomous(self, request=None, session_id=None):
        return self.autonomous.resume(request, session_id=session_id)

    def run(self, request, session_id=None):
        if session_id is None:
            session_id = self.sessions.create(title=request[:80])
        else:
            self.sessions.load(session_id)
        previous = self.sessions.recent(session_id, 12)
        self.sessions.append(session_id, 'user', request)
        history=[]
        self.planner.ensure(request)
        available = ['list_files','read_file','write_file','edit_file','preview_edit','rollback_edit','research','run_command','run_tests','diagnose','remember','recall','plan','resume_plan','project_context','app_factory','build_app','assets','visual_edit','workflow','visual_workflow','session','projects','tasks','parallel_tasks','autonomous','deploy','artifacts','versions','studio','release_intelligence','knowledge_graph','impact','change_intelligence','regression_intelligence','repair_learning','predictive_engineering','preventive_engineering','engineering_guardrails','adaptive_guardrails','self_healing_guardrails','engineering_recovery_planner','recovery_execution','brain_memory','brain_meta_reasoning','predictive_cognitive_recovery','adaptive_cognitive_cycle','training_lab','research_plan','code_repair','regression_engineering','research_execution','project_blueprint','project_orchestrator','app_evolution','decompose','scheduler','resources','monitor','brain_learning','local_access','local_execution','local_preview','visual_contract','app_build_coordinator','questions','api','media','multimodal','local_models']
        for step in range(1, self.max_steps+1):
            prompt = json.dumps({
                'request': request,
                'step': step,
                'available_tools': available,
                'session_id': session_id,
                'conversation': previous,
                'research_available': self.researcher.available(),
                'recent_memory': [m.__dict__ for m in self.memory.recent(6)],
                'plan': self.planner.context(),
                'project_context': self.context.format(request, limit=4, max_total_chars=4500),
                'history': history[-8:],
                'instruction': 'Use diagnose após uma execução/teste com falha para transformar o erro em diagnóstico estruturado. Ao pesquisar, preserve fontes, URLs, títulos e trechos relevantes.'
            }, ensure_ascii=False)
            raw=self.model.ask(prompt)
            try: action=json.loads(raw)
            except json.JSONDecodeError:
                return {'status':'model_output_invalid','step':step,'raw':raw,'history':history}
            if 'final' in action:
                self.planner.plan and setattr(self.planner.plan, 'status', 'completed')
                self.planner._save()
                self.sessions.append(session_id, 'assistant', str(action['final']), {'status': 'completed'})
                self.sessions.set_state(session_id, plan_id=(self.planner.plan.id if self.planner.plan else None), last_status='completed')
                return {'status':'completed','step':step,'result':action['final'],'history':history,'session_id':session_id}
            tool=action.get('tool'); args=action.get('args',{})
            try:
                result=self._call(tool,args)
                history.append({'tool':tool,'args':args,'result':result})
                self.sessions.append(session_id, 'tool', json.dumps({'tool': tool, 'result': result}, ensure_ascii=False), {'tool': tool})
                self.planner.observe(tool, result)
            except Exception as e:
                history.append({'tool':tool,'args':args,'error':str(e)})
                self.sessions.append(session_id, 'tool_error', str(e), {'tool': tool})
        self.sessions.set_state(session_id, plan_id=(self.planner.plan.id if self.planner.plan else None), last_status='max_steps')
        return {'status':'max_steps','step':self.max_steps,'history':history,'session_id':session_id}
