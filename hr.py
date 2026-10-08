import streamlit as st
import pandas as pd

st.set_page_config(page_title="결원 자동 충원 시스템", page_icon="🚒", layout="wide")
st.title("🚒 결원 자동 충원 및 스마트 인사배치 시스템")
st.markdown("기존 팀별 잔류 인원과 신규 전입 인원을 합산하여 구급자격, 계급, 성별에 따라 결원을 자동으로 배치합니다.")

# 샘플 템플릿 다운로드용 데이터
@st.cache_data
def get_template_csv():
    df = pd.DataFrame({
        "이름": ["홍길동", "김소방", "이구급", "박구조"],
        "성별": ["남", "여", "남", "여"],
        "계급": ["소방위", "소방장", "소방교", "소방사"],
        "구급자격": ["해당없음", "간호사", "1급", "해당없음"],
        "소속팀": ["1팀", "2팀", "신규전입", "신규전입"] 
    })
    return df.to_csv(index=False).encode('utf-8-sig')

with st.sidebar:
    st.header("사용 가이드")
    st.markdown("""
    1. 아래 템플릿을 다운로드하여 양식에 맞게 **현재 잔류 인원**과 **신규 전입 인원**을 작성합니다.
    2. 타서 전출 등으로 빠진 결원 인원은 명단에서 삭제합니다.
    3. 새로 배치될 인원의 '소속팀'은 **신규전입**으로 입력합니다.
    """)
    st.download_button("데이터 양식(CSV) 다운로드", get_template_csv(), "인사배치양식.csv", "text/csv")
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
        st.write("📋 **현재 잔류 인원 현황 (결원 발생 후)**")
        st.dataframe(df[df['소속팀'].isin(['1팀', '2팀', '3팀'])])
    with col2:
        st.write("🆕 **신규 전입 인원 현황 (배치 대기)**")
        st.dataframe(df[df['소속팀'] == '신규전입'])

    if st.button("자동 인사 배치 실행", type="primary"):
        existing = df[df['소속팀'].isin(['1팀', '2팀', '3팀'])].copy()
        new_staff = df[df['소속팀'] == '신규전입'].copy()
        teams = ['1팀', '2팀', '3팀']
        
        # 신규 인원 배치 로직
        for index, person in new_staff.iterrows():
            assigned = False
            
            # 1순위: 구급 자격자 최우선 배치 (간호사, 1급, 2급)
            if person['구급자격'] in ['간호사', '1급', '2급']:
                for t in teams:
                    team_staff = existing[existing['소속팀'] == t]
                    # 해당 팀에 동일한 구급자격이 없는 경우 배치
                    if not (team_staff['구급자격'] == person['구급자격']).any():
                        person['소속팀'] = t
                        existing = pd.concat([existing, pd.DataFrame([person])])
                        assigned = True
                        break
            
            if assigned:
                continue
                
            # 2순위: 계급 안배 및 3순위 성별 안배
            rank_counts = {t: len(existing[(existing['소속팀'] == t) & (existing['계급'] == person['계급'])]) for t in teams}
            min_rank_count = min(rank_counts.values())
            candidate_teams = [t for t, count in rank_counts.items() if count == min_rank_count]
            
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
