import argparse, json
from .agent import Agent
p=argparse.ArgumentParser(); p.add_argument('request', nargs='*'); p.add_argument('--workspace',default='workspace'); p.add_argument('--max-steps',type=int,default=12); p.add_argument('--session', help='ID da sessão persistente'); p.add_argument('--new-session', action='store_true'); p.add_argument('--list-sessions', action='store_true'); p.add_argument('--resume', action='store_true'); p.add_argument('--cycle-status', action='store_true'); p.add_argument('--ui', action='store_true'); p.add_argument('--autonomous', action='store_true'); p.add_argument('--autonomous-status', action='store_true'); p.add_argument('--build-app', action='store_true')
a=p.parse_args(); agent=Agent(a.workspace,max_steps=a.max_steps)
if a.ui:
    from .ui import AuroraUI
    AuroraUI(agent).serve()
elif a.list_sessions: print(json.dumps(agent.sessions.list(), ensure_ascii=False, indent=2))
elif a.cycle_status: print(json.dumps(agent.cycle.status(), ensure_ascii=False, indent=2))
elif a.autonomous_status: print(json.dumps(agent.autonomous.status(), ensure_ascii=False, indent=2))
elif a.build_app:
    print(json.dumps(agent._call('build_app', {'description': ' '.join(a.request), 'run_tests': True}), ensure_ascii=False, indent=2))
else:
    sid = None if a.new_session else a.session
    if a.autonomous:
        if a.resume:
            result = agent.resume_autonomous(' '.join(a.request) or None, session_id=sid)
        else:
            result = agent.run_autonomous(' '.join(a.request), session_id=sid)
    elif a.resume:
        result = agent.resume_cycle(' '.join(a.request) or None, session_id=sid)
    else:
        result = agent.run_cycle(' '.join(a.request), session_id=sid)
    print(json.dumps(result, ensure_ascii=False, indent=2))
