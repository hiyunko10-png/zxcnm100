import json
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="우리집 오늘판",page_icon="🏡",layout="centered")
st.title("🏡 우리집 오늘판")
st.caption("오늘의 식사와 귀가 · 오는 길에 부탁해")
FILE=Path('home_today.json')

@st.cache_resource
def lock():
 return threading.Lock()

def empty():
 return {'members':[],'days':{},'tasks':[]}

def read_disk():
 if not FILE.exists(): return {'revision':0,'data':empty()}
 return json.loads(FILE.read_text(encoding='utf-8'))

def save(data,revision):
 try:
  with lock():
   if read_disk()['revision']!=revision:
    st.warning('다른 가족이 먼저 수정했어요. 최신 화면에서 다시 시도해주세요.')
    st.stop()
   tmp=FILE.with_suffix('.tmp')
   tmp.write_text(json.dumps({'revision':revision+1,'data':data},ensure_ascii=False),encoding='utf-8')
   tmp.replace(FILE)
 except (OSError,ValueError,KeyError):
  st.error('저장하지 못했어요. 새로고침 후 다시 시도해주세요.');st.stop()
 st.rerun()

try:
 with lock(): row=read_disk()
except (OSError,ValueError):
 st.error('저장 파일을 읽지 못했어요. 기존 데이터를 보호하기 위해 실행을 중단합니다.');st.stop()
d=row['data'];revision=row['revision']
# 한국 기준 날짜 (별도 외부 서비스 불필요)
from datetime import timezone
today=datetime.now(timezone(timedelta(hours=9))).date()
with st.sidebar:
 st.header('우리 가족')
 if st.button('🔄 최신 내용 보기',use_container_width=True):st.rerun()
 with st.form('member',clear_on_submit=True):
  name=st.text_input('가족 별명 추가',max_chars=20).strip()
  if st.form_submit_button('추가'):
   if not name:st.warning('별명을 입력해주세요.')
   elif name in d['members']:st.info('이미 등록한 별명이에요.')
   else:d['members'].append(name);save(d,revision)
 st.caption(' · '.join(d['members']) or '별명을 추가하면 바로 시작할 수 있어요.')
 st.info('로그인 없는 공용 공간입니다. 이 앱 주소를 아는 사람은 모두 내용을 보고 수정할 수 있어요.')
 st.caption('서버에 임시 저장돼요. 서버 초기화·재배포 시 사라질 수 있으니 백업해주세요. 열린 다른 화면은 자동 갱신되지 않습니다.')
 st.download_button('💾 전체 백업',json.dumps(d,ensure_ascii=False,indent=2),'today_backup.json','application/json')
 with st.expander('백업 복원'):
  upload=st.file_uploader('JSON 백업',type=['json'])
  confirm=st.checkbox('현재 내용을 백업으로 교체합니다')
  if st.button('복원',disabled=not confirm):
   try:
    if upload is None:raise ValueError()
    v=json.load(upload)
    assert isinstance(v,dict) and isinstance(v.get('members'),list) and isinstance(v.get('days'),dict) and isinstance(v.get('tasks'),list)
    assert all(isinstance(n,str) and 0<len(n)<=20 for n in v['members'])
    assert len(v['members'])==len(set(v['members']))
    for day,entries in v['days'].items():
     date.fromisoformat(day);assert isinstance(entries,dict)
     for n,e in entries.items():
      assert isinstance(n,str) and isinstance(e,dict) and e.get('meal') in ['먹어요','안 먹어요','아직 몰라요'] and isinstance(e.get('arrival'),str)
    ids=[]
    for t in v['tasks']:
     assert isinstance(t,dict)
     assert all(isinstance(t.get(k),str) for k in ['id','title','category','due','owner','created'])
     assert t['title'] and isinstance(t.get('done'),bool)
     date.fromisoformat(t['due']);ids.append(t['id'])
    assert len(ids)==len(set(ids))
   except (ValueError,TypeError,AssertionError,KeyError):st.error('올바른 백업 파일을 선택해주세요.')
   else:save(v,revision)

if not d['members']:
 st.info('👈 왼쪽 메뉴에서 가족 별명을 추가해주세요. 휴대폰에서는 왼쪽 위 사이드바 버튼을 누르세요.')
 st.subheader('오늘 저녁, 몇 명이 먹을까요?')
 st.write('가족은 저녁 여부와 귀가 시간을 남기고, 필요한 물건이나 집안일은 서로 맡을 수 있어요.')
 st.stop()
actor=st.selectbox('나는 누구인가요?',d['members'])
a,b,c=st.tabs(['☀️ 오늘','🛒 오는 길에 부탁해','📅 이번 주'])
with a:
 st.subheader(today.strftime('%m월 %d일')+' · 우리집 오늘')
 key=today.isoformat();entries=d['days'].get(key,{})
 eat=sum(entries.get(n,{}).get('meal')=='먹어요' for n in d['members'])
 no=sum(entries.get(n,{}).get('meal')=='안 먹어요' for n in d['members'])
 unsure=len(d['members'])-eat-no
 cols=st.columns(3)
 cols[0].metric('🍚 저녁 확정',f'{eat}명');cols[1].metric('외식·불참',f'{no}명');cols[2].metric('미정·미응답',f'{unsure}명')
 st.caption('미정·미응답은 식사 불참으로 계산하지 않아요. 응답은 날짜별로 따로 저장됩니다.')
 current=entries.get(actor,{})
 with st.form('status'):
  statuses=['아직 몰라요','먹어요','안 먹어요']
  meal=st.radio('오늘 집에서 저녁 먹나요?',statuses,index=statuses.index(current.get('meal','아직 몰라요')),horizontal=True)
  options=['미정','집에 있어요']+[f'{h:02d}:{m:02d}' for h in range(24) for m in [0,30]]
  old=current.get('arrival','미정')
  arrival=st.selectbox('귀가 예정시간',options,index=options.index(old) if old in options else 0)
  if st.form_submit_button('내 상태 저장',type='primary',use_container_width=True):
   d['days'].setdefault(key,{})[actor]={'meal':meal,'arrival':arrival};save(d,revision)
 st.markdown('#### 가족 소식')
 for n in d['members']:
  e=entries.get(n,{})
  with st.container(border=True):
   st.write(f"**{n}** · 저녁 {e.get('meal','미응답')} · 귀가 {e.get('arrival','미정')}")
 urgent=[t for t in d['tasks'] if not t['done'] and t['due']<=key]
 if urgent:
  st.markdown('#### 오늘까지 챙길 부탁')
  for t in sorted(urgent,key=lambda t:(bool(t['owner']),t['due'])):
   st.write(f"{'⚠️ 기한 지남 · ' if t['due']<key else ''}{t['title']} — {t['owner'] or '🙋 담당자 없음'}")
with b:
 st.subheader('🛒 오는 길에 부탁해')
 st.caption('장보기뿐 아니라 반품·준비물·집안일도 함께 챙겨요.')
 with st.form('new_task',clear_on_submit=True):
  title=st.text_input('무엇이 필요한가요?',placeholder='예: 우유 1개 사오기 / 체육복 세탁하기',max_chars=120).strip()
  category=st.selectbox('종류',['장보기','집안일','반품·택배','준비물','기타'])
  due=st.date_input('언제까지?',today)
  if st.form_submit_button('부탁 등록',type='primary'):
   if not title:st.warning('부탁할 내용을 입력해주세요.')
   else:
    d['tasks'].append({'id':uuid.uuid4().hex,'title':title,'category':category,'due':due.isoformat(),'owner':'','done':False,'created':actor});save(d,revision)
 view=st.radio('보기',['할 일 전체','내가 맡은 일','완료한 일'],horizontal=True)
 tasks=[t for t in d['tasks'] if (t['done'] if view=='완료한 일' else not t['done'] and (view!='내가 맡은 일' or t['owner']==actor))]
 tasks.sort(key=lambda t:(bool(t['owner']),t['due']))
 if not tasks:st.success('이 목록에는 남은 부탁이 없어요!')
 for t in tasks:
  with st.container(border=True):
   st.markdown('**'+t['title']+'**')
   st.caption(f"{t['category']} · {t['due']}까지 · 부탁한 가족: {t['created']}")
   st.write('담당: '+(t['owner'] or '아직 없어요 🙋'))
   if not t['done'] and t['due']<today.isoformat():st.warning('기한이 지났어요.')
   x,y=st.columns(2)
   if not t['done']:
    if not t['owner']:
     if x.button('🙋 내가 할게',key='claim'+t['id'],use_container_width=True):t['owner']=actor;save(d,revision)
    elif t['owner']==actor:
     if x.button('맡기 취소',key='release'+t['id'],use_container_width=True):t['owner']='';save(d,revision)
    if t['owner']==actor:
     if y.button('✅ 완료',key='done'+t['id'],use_container_width=True):t['done']=True;save(d,revision)
   else:
    if x.button('다시 할 일로',key='undo'+t['id'],use_container_width=True):t['done']=False;save(d,revision)
with c:
 st.subheader('📅 이번 주에 챙길 일')
 monday=today-timedelta(days=today.weekday())
 for i in range(7):
  day=monday+timedelta(days=i);key=day.isoformat()
  with st.container(border=True):
   st.markdown(f"**{day.strftime('%m/%d')} ({'월화수목금토일'[i]}){' · 오늘' if day==today else ''}**")
   entries=d['days'].get(key,{})
   eating=[n for n in d['members'] if entries.get(n,{}).get('meal')=='먹어요']
   st.caption('저녁 식사 확정: '+(', '.join(eating) or '아직 없음'))
   items=[t for t in d['tasks'] if t['due']==key]
   if not items:st.write('등록된 부탁 없음')
   for t in items:st.write(f"{'✅' if t['done'] else '⬜'} {t['title']} · {t['owner'] or '담당 미정'}")
