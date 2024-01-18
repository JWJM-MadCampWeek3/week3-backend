![35116a0e826](https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/5377fda6-7ee2-4b3a-a0a8-b66e82c5aa22)

![Builder (6)](https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/2b58c71f-f213-438c-8c66-e76133176af3)

# Builder

## 그룹을 build.

## 문제를 build.

## 실력을 build.

---

- backjoon id를 포함하는 자체 로그인을 구현했습니다.
- 타이머 기능을 구현하여 그룹 내 사람들과 함께 공부하는 느낌을 받을 수 있습니다.
- 랭킹시스템을 구현하여 알고리즘 공부의 동기부여를 얻을 수 있게 하였습니다.
- 문제집 기능으로 좋은 문제를 저장하고, 그룹원들과 공유할 수 있습니다.

---

### a. 개발 팀원

2023W 몰입캠프 Week 3 1분반

- 서재원 - 한양대학교 컴퓨터소프트웨어학부 22학번
- 박정민 - KAIST 전산학부 21학번

---

### b. 개발 환경

- Language : React, Typescript, FastAPI
- DB : MongoDB
- target : web
- IDE : Visual Studio Code

---

### c. 웹 소개

### Login/Signup

### Major Features

<img width="703" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/82de7a11-55e8-4177-ba33-71975ae69bc5">

- signup 창에서는 아이디, 비밀번호, 닉네임, 백준 아이디를 입력받습니다. 중복검사를 지원합니다.
- login 창에서 db에 저장되어 있는 아이디와 비밀번호를 입력하면 메인화면으로 이동합니다.

### 기술 설명

- signup 시 [solved.ac](http://solved.ac/) api와 연동되어 백준 아이디를 참조해서 백준 유저 정보를 db에 저장합니다.

### 사이드바

<img width="263" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/5b46629c-788a-431a-b9a1-3aacfe3f3cd3">

### Major Features

- 사이드바에서는 유저의 프로필을 보여줍니다.
- 공부한 시간을 측정하고, 그룹원들과 같이 공부할 수 있게 하는 타이머가 있습니다.
- 내가 풀 문제들, 오늘 풀 문제들을 모아놓은 창이 있습니다.
- 문제들은 자기가 속한 그룹의 문제집에 넣어서 그룹원들과 같이 풀 수 있습니다.

### 기술 설명

- 타이머의 시작버튼을 눌렀을 때와 정지 버튼을 눌렀을 때의 시간 차이를 datetime의 utcnow()의 차이를 구해서 DB에 저장합니다. 이 차이를 duration에 더해가면서 총 공부시간을 측정합니다. 총 공부시간은 유저별, 날짜별로 관리됩니다.

### Group

<img width="699" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/5db86063-b6fb-4bea-9fb3-600532adb0c1">


### Major Features

- 그룹별로 그룹원들이 현재 공부를 하고 있는지, 아닌지 볼 수 있습니다.
- 그룹에서 풀면 좋을 문제들을 보여줍니다
- 그룹원들의 목록을 보여줍니다.

### 기술설명

- 그룹원들의 정보를 저장해놓은 DB를 참조해서 그룹원들 별로 공부를 하고 있는지 여부를 화면에 보여줍니다.

### recommend


<img width="699" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/a79a080e-c85d-47a1-b41f-a2269d292a78">

### Major Features

- 추천 버튼을 누르면 유저에게 풀 알고리즘을 선택받습니다.
- 그러면 유저의 수준에 맞는 10개의 문제가 추천됩니다.
- 문제를 클릭하면 내 문제집에 넣을 수 있습니다.

### 기술설명

- DB에 저장된 많은 문제들을 유저의 티어의 위로 3개, 아래로 3개 사이의 범위를 설정하고, 유저가 선택한 알고리즘을 검색 query로 사용하여 문제를 10개 검색합니다.

### Ranking

<img width="700" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/30b5d8ba-f664-4423-af6d-56e9703994f0">

### Major Features

- 그룹 별로 해당 그룹에 속한 그룹원들의 랭킹을 볼 수 있습니다.
- 그룹원들의 닉네임, 백준아이디, 총 푼 문제수, 공부시간, 티어를 볼 수 있습니다.
- 일간 랭킹과, 월간 랭킹을 지원합니다.

### 기술 설명

- DB에 저장되어 있는 duration들을 조건에 맞게 가져와서 sorting해 화면에 보여줍니다.

### Problems

<img width="696" alt="image" src="https://github.com/JWJM-MadCampWeek3/week3-backend/assets/149568715/09319266-693b-4255-9581-7e270dc89e04">

### Major Features

- 개인이 풀면 좋을 문제들을 모아서 보여줍니다.
- todo Problem으로 곧 풀 문제들을 따로 보여줍니다.
- 문제를 클릭하면 자기가 속한 그룹 문제집에 문제를 추가할 수 있습니다.

### 기술 설명

- 사용자별로 DB의 Problems, todoProblems attribute로 문제집들을 관리합니다.
- 그룹별로 DB의 Problems attribute로 문제집을 관리합니다.

  


[API List](https://www.notion.so/47a2a296ccd845f0813fed86cc5310f1?pvs=21)

[DATA](https://www.notion.so/7221daf7021943aa883a9e77f3d57dff?pvs=21)


