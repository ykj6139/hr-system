import streamlit as st
import pandas as pd

st.set_page_config(page_title="결원 자동 충원 시스템", page_icon="🚒", layout="wide")
st.title("🚒 결원 자동 충원 및 스마트 인사배치 시스템 (희망팀 반영)")
st.markdown("기존 잔류 인원과 배치 대기 인원을 합산하여 구급자격, 계급, 성별, 그리고 **개인별 희망팀**을 종합적으로 고려해 자동 배치합니다.")

# 샘플 템플릿 다운로드용 데이터 (희망팀 컬럼 추가)
@st.cache_data
def get_template_csv():
    df = pd.DataFrame({
        "이름": ["홍길동", "김소방", "이구급", "박구조", "최대원"],
        "성별": ["남", "여", "남", "여", "남"],
        "계급": ["소방위", "소방장", "소방교", "소방사", "소방교"],
        "구급자격": ["해당없음", "간호사", "1급", "해당없음", "해당없음"],
        "소속팀": ["1팀", "2팀", "배치대기", "배치대기", "배치대기"],
        "희망팀": ["해당없음", "해당없음", "1팀", "3팀", "상관없음"]
    })
    return df.to_csv(index=False).encode('utf-8-sig')

with st.sidebar:
    st.header("사용 가이드")
    st.markdown("""
    1. 아래 템플릿을 다운로드하여 **현재 잔류 인원**과 **이동/전입 인원**을 작성합니다.
    2. 기존 직원 중 팀 이동 희망자와 신규 전입자는 '소속팀'을 **배치대기**로 입력합니다.
    3. 특정 팀 배치를 원하면 '희망팀'에 **1팀, 2팀, 3팀**을 적고, 없으면 **상관없음**으로 적습니다.
    """)
    st.download_button("데이터 양식(CSV) 다운로드", get_template_csv(), "인사배치양식_희망팀.csv", "text/csv")
    st.markdown("---")
    st.markdown("개발: 장계119안전센터")

st.subheader("1. 인사 데이터 업로드")
uploaded_file = st.file_uploader("작성한 인사 데이터(CSV 또는 엑셀)를 업로드하세요.", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("📋 **현재 잔류 인원 현황 (이동 없음)**")
        st.dataframe(df[df['소속팀'].isin(['1팀', '2팀', '3팀'])])
    with col2:
        st.write("🆕 **배치 대기 인원 (신규 및 이동 희망자)**")
        st.dataframe(df[df['소속팀'] == '배치대기'])

    if st.button("자동 인사 배치 실행", type="primary"):
        existing = df[df['소속팀'].isin(['1팀', '2팀', '3팀'])].copy()
        new_staff = df[df['소속팀'] == '배치대기'].copy()
        teams = ['1팀', '2팀', '3팀']
        
        # 배치 대기 인원 자동 배치 로직
        for index, person in new_staff.iterrows():
            assigned = False
            pref_team = str(person.get('희망팀', '상관없음')).strip()
            
            # 1순위: 구급 자격자 배치 (간호사, 1급, 2급)
            if person['구급자격'] in ['간호사', '1급', '2급']:
                # 본인 희망팀에 해당 구급자격 결원이 있는지 우선 확인
                if pref_team in teams:
                    team_staff = existing[existing['소속팀'] == pref_team]
                    if not (team_staff['구급자격'] == person['구급자격']).any():
                        person['소속팀'] = pref_team
                        existing = pd.concat([existing, pd.DataFrame([person])])
                        assigned = True
                
                # 희망팀에 자리가 없거나 희망팀이 '상관없음'인 경우 빈 곳으로 배치
                if not assigned:
                    for t in teams:
                        team_staff = existing[existing['소속팀'] == t]
                        if not (team_staff['구급자격'] == person['구급자격']).any():
                            person['소속팀'] = t
                            existing = pd.concat([existing, pd.DataFrame([person])])
                            assigned = True
                            break
            
            if assigned:
                continue
                
            # 2순위: 일반 대원 배치 (계급 및 성별 밸런스 + 희망팀 반영)
            rank_counts = {t: len(existing[(existing['소속팀'] == t) & (existing['계급'] == person['계급'])]) for t in teams}
            min_rank_count = min(rank_counts.values())
            
            # 해당 계급이 가장 적은 팀(들)을 후보로 선정
            candidate_teams = [t for t, count in rank_counts.items() if count == min_rank_count]
            
            # 후보 팀 중에 본인의 희망팀이 있다면 우선 배정
            if pref_team in candidate_teams:
                target_team = pref_team
            else:
                # 희망팀이 후보에 없거나 '상관없음'인 경우 성별 밸런스로 결정
                if len(candidate_teams) == 1:
                    target_team = candidate_teams[0]
                else:
                    gender_counts = {t: len(existing[(existing['소속팀'] == t) & (existing['성별'] == person['성별'])]) for t in candidate_teams}
                    target_team = min(gender_counts, key=gender_counts.get)
            
            person['소속팀'] = target_team
            existing = pd.concat([existing, pd.DataFrame([person])])

        st.success("✅ 결원 자동 배치가 완료되었습니다.")
        
        st.subheader("2. 배치 결과 종합 현황")
        st.dataframe(existing)
        
        st.write("📊 **최종 팀별 인원 통계**")
        stats = existing.groupby(['소속팀', '계급']).size().unstack(fill_value=0)
        st.dataframe(stats)
        
        result_csv = existing.to_csv(index=False).encode('utf-8-sig')
        st.download_button("최종 배치 결과 다운로드(CSV)", result_csv, "최종_인사배치결과.csv", "text/csv")