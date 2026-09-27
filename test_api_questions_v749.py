import json
from aurora.agent import Agent
class FakeModel:
    def ask(self,prompt,inputs=None):
        return json.dumps({'questions':[{'id':1,'type':'multiple_choice','difficulty':'easy','question':'Quanto é 2+2?','alternatives':['2','3','4','5'],'answer':'4','explanation':'2+2=4'}]})
def test_question_generator(tmp_path):
    a=Agent(workspace=str(tmp_path),model=FakeModel()); r=a._call('questions',{'action':'generate','topic':'matemática','count':1,'difficulty':'easy'}); assert r['ok'] and r['questions'][0]['answer']=='4'
def test_api_key_and_endpoint(tmp_path):
    a=Agent(workspace=str(tmp_path),model=FakeModel()); k=a._call('api',{'action':'create_key','name':'estudos'})['key']; assert k.startswith('aurora_sk_'); code,p=a.api.handle('POST','/v1/questions',{'topic':'matemática','count':1},k); assert code==200 and p['questions']; assert a.api.handle('POST','/v1/questions',{'topic':'x'},'bad')[0]==401
