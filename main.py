<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>알리미2 - 입찰 및 정비사업 통합 모니터링</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        body { font-family: 'Pretendard', sans-serif; }
        .gold-glow { box-shadow: 0 0 15px rgba(234, 179, 8, 0.35); }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen pb-12">

    <!-- 로그인 보안 모달 -->
    <div id="auth-overlay" class="fixed inset-0 bg-slate-900/90 backdrop-blur-md z-[100] flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 border border-slate-100 text-center">
            <div class="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 text-blue-600">
                <i data-lucide="lock" class="w-7 h-7"></i>
            </div>
            <h2 class="text-xl font-bold text-slate-900 mb-1">알리미2 인증</h2>
            <p class="text-xs text-slate-500 mb-6">전용 대시보드입니다. 비밀번호를 입력해 주세요.</p>
            
            <form onsubmit="verifyPassword(event)" class="space-y-4">
                <div>
                    <input type="password" id="auth-password" placeholder="접속 비밀번호 입력" class="w-full px-4 py-3 border border-slate-300 rounded-xl text-center text-base focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono">
                </div>
                <p id="auth-error" class="text-xs text-rose-500 hidden font-semibold">⚠️ 비밀번호가 올바르지 않습니다.</p>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition shadow-md">
                    대시보드 접속하기
                </button>
            </form>
            <p class="text-[11px] text-slate-400 mt-6">기본 비밀번호: <code class="bg-slate-100 px-1 py-0.5 rounded text-slate-600">1234</code></p>
        </div>
    </div>

    <!-- 대시보드 메인 -->
    <div id="dashboard-main" class="hidden">
        <header class="bg-slate-900 text-white sticky top-0 z-50 shadow-md">
            <div class="max-w-7xl mx-auto px-4 py-4 flex flex-wrap justify-between items-center gap-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-600 rounded-lg">
                        <i data-lucide="building-2" class="w-6 h-6 text-white"></i>
                    </div>
                    <div>
                        <h1 class="text-xl font-bold tracking-tight text-white">알리미2 - 입찰·정비사업 아카이브</h1>
                        <p class="text-xs text-slate-400">나라장터 공고 누적 모니터링 & 캘린더</p>
                    </div>
                </div>

                <div class="flex items-center gap-3">
                    <button onclick="loadNotices()" class="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-lg text-sm font-medium border border-slate-700 transition">
                        <i id="refresh-icon" data-lucide="refresh-cw" class="w-4 h-4"></i>
                        <span>새로고침</span>
                    </button>

                    <div class="bg-slate-800 p-1 rounded-lg border border-slate-700 flex items-center">
                        <button id="btn-user-mode" onclick="setRole('user')" class="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white transition">👤 사용자</button>
                        <button id="btn-admin-mode" onclick="setRole('admin')" class="px-3 py-1.5 rounded-md text-xs font-semibold text-slate-400 hover:text-white transition">⚙️ 관리자</button>
                    </div>

                    <button onclick="logout()" title="로그아웃" class="p-2 bg-slate-800 hover:bg-rose-900/50 text-slate-400 hover:text-rose-300 rounded-lg border border-slate-700 transition">
                        <i data-lucide="log-out" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 mt-6">
            <div id="status-bar" class="hidden mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-800 text-xs rounded-lg flex items-center justify-between">
                <span class="flex items-center gap-2"><i data-lucide="info" class="w-4 h-4 text-blue-600"></i><span id="status-msg">데이터를 불러왔습니다.</span></span>
                <button onclick="document.getElementById('status-bar').classList.add('hidden')" class="text-blue-500 hover:text-blue-700">✕</button>
            </div>

            <!-- 검색 및 탭 바 -->
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
                <div class="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div class="flex flex-wrap gap-2 w-full md:w-auto">
                        <button onclick="setTab('all')" id="tab-all" class="tab-btn px-4 py-2.5 rounded-lg text-sm font-bold bg-blue-600 text-white shadow-sm">📋 전체공고현황</button>
                        <button onclick="setTab('bid')" id="tab-bid" class="tab-btn px-4 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100">🏛️ 본공고</button>
                        <button onclick="setTab('spec')" id="tab-spec" class="tab-btn px-4 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100">🔍 사전규격</button>
                        <button onclick="setTab('plan')" id="tab-plan" class="tab-btn px-4 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100">📌 발주계획</button>
                    </div>

                    <div class="relative w-full md:w-72">
                        <input type="text" id="search-input" oninput="render()" placeholder="공고명, 기관명 검색..." class="w-full pl-9 pr-4 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <i data-lucide="search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5"></i>
                    </div>
                </div>
            </div>

            <!-- 메인 레이아웃: 좌측 공고 목록 / 우측 캘린더 -->
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <!-- 공고 리스트 영역 (3칸) -->
                <div class="lg:col-span-3" id="notice-container"></div>

                <!-- 우측 캘린더 영역 (1칸) -->
                <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm h-fit sticky top-24">
                    <div class="flex justify-between items-center mb-4">
                        <h3 id="cal-month-title" class="font-bold text-slate-800 text-base">2026년 10월</h3>
                        <div class="flex gap-1">
                            <button onclick="changeMonth(-1)" class="p-1.5 hover:bg-slate-100 rounded text-slate-600"><i data-lucide="chevron-left" class="w-4 h-4"></i></button>
                            <button onclick="changeMonth(1)" class="p-1.5 hover:bg-slate-100 rounded text-slate-600"><i data-lucide="chevron-right" class="w-4 h-4"></i></button>
                        </div>
                    </div>
                    <!-- 요일 헤더 -->
                    <div class="grid grid-cols-7 text-center text-xs font-semibold text-slate-400 mb-2">
                        <span class="text-rose-500">일</span><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span><span class="text-blue-500">토</span>
                    </div>
                    <!-- 날짜 그리드 -->
                    <div id="cal-days-grid" class="grid grid-cols-7 gap-1 text-center text-xs"></div>
                    <div class="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                        <span>📅 날짜 클릭시 해당일 공고 필터</span>
                        <button onclick="clearDateFilter()" class="text-blue-600 font-semibold hover:underline">전체 보기</button>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        const SITE_PASSWORD = "1234";
        const ADMIN_PASSWORD = "admin1234";
        let notices = [];
        let currentRole = 'user';
        let currentTab = 'all';
        let selectedDateFilter = null; // 캘린더 날짜 필터
        let calYear = new Date().getFullYear();
        let calMonth = new Date().getMonth();

        function checkAuth() {
            if (sessionStorage.getItem('authenticated') === 'true') {
                document.getElementById('auth-overlay').classList.add('hidden');
                document.getElementById('dashboard-main').classList.remove('hidden');
                loadNotices();
            } else {
                document.getElementById('auth-overlay').classList.remove('hidden');
                document.getElementById('dashboard-main').classList.add('hidden');
            }
            lucide.createIcons();
        }

        function verifyPassword(event) {
            event.preventDefault();
            if (document.getElementById('auth-password').value === SITE_PASSWORD) {
                sessionStorage.setItem('authenticated', 'true');
                checkAuth();
            } else {
                document.getElementById('auth-error').classList.remove('hidden');
            }
        }

        function logout() {
            sessionStorage.removeItem('authenticated');
            checkAuth();
        }

        async function loadNotices() {
            const icon = document.getElementById('refresh-icon');
            if(icon) icon.classList.add('animate-spin');
            try {
                const res = await fetch('notices.json?t=' + new Date().getTime());
                if (res.ok) {
                    notices = await res.json();
                }
            } catch (e) {
                console.log("notices.json 로드 대기 중...");
            }
            if(icon) icon.classList.remove('animate-spin');
            render();
            renderCalendar();
        }

        function formatPrice(price) {
            if (!price || price === 0) return '민간/기타';
            return (price / 100000000).toFixed(1) + '억 원';
        }

        // 본공고 D-day 계산 함수
        function getDday(limitDateStr) {
            if (!limitDateStr || limitDateStr === '-') return null;
            const today = new Date();
            today.setHours(0,0,0,0);
            const limitDate = new Date(limitDateStr);
            limitDate.setHours(0,0,0,0);
            
            const diffTime = limitDate - today;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays > 0) return `D-${diffDays}`;
            if (diffDays === 0) return `D-Day`;
            return `마감됨`;
        }

        function setRole(role) {
            if (role === 'admin' && currentRole !== 'admin') {
                if (prompt("⚙️ 관리자 비밀번호를 입력해 주세요:") !== ADMIN_PASSWORD) {
                    alert("⚠️ 비밀번호가 틀렸습니다.");
                    return;
                }
            }
            currentRole = role;
            document.getElementById('btn-user-mode').className = role === 'user' ? 'px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white transition' : 'px-3 py-1.5 rounded-md text-xs font-semibold text-slate-400 hover:text-white transition';
            document.getElementById('btn-admin-mode').className = role === 'admin' ? 'px-3 py-1.5 rounded-md text-xs font-semibold bg-amber-600 text-white transition' : 'px-3 py-1.5 rounded-md text-xs font-semibold text-slate-400 hover:text-white transition';
            render();
        }

        function setTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.className = 'tab-btn px-4 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100');
            document.getElementById(`tab-${tab}`).className = 'tab-btn px-4 py-2.5 rounded-lg text-sm font-bold bg-blue-600 text-white shadow-sm';
            render();
        }

        function filterByDate(dateStr) {
            selectedDateFilter = selectedDateFilter === dateStr ? null : dateStr;
            render();
            renderCalendar();
        }

        function clearDateFilter() {
            selectedDateFilter = null;
            render();
            renderCalendar();
        }

        // 캘린더 렌더링
        function renderCalendar() {
            const titleEl = document.getElementById('cal-month-title');
            const gridEl = document.getElementById('cal-days-grid');
            titleEl.innerText = `${calYear}년 ${calMonth + 1}월`;

            const firstDayIndex = new Date(calYear, calMonth, 1).getDay();
            const totalDays = new Date(calYear, calMonth + 1, 0).getDate();

            let daysHtml = '';
            for (let i = 0; i < firstDayIndex; i++) {
                daysHtml += `<div></div>`;
            }

            for (let day = 1; day <= totalDays; day++) {
                const mStr = String(calMonth + 1).padStart(2, '0');
                const dStr = String(day).padStart(2, '0');
                const dateStr = `${calYear}-${mStr}-${dStr}`;

                // 해당 날짜에 공고가 있는지 확인
                const hasNotice = notices.some(n => n.dateNotice === dateStr);
                const isSelected = selectedDateFilter === dateStr;

                let btnClass = "w-7 h-7 mx-auto rounded-full flex items-center justify-center text-xs font-medium transition ";
                if (isSelected) {
                    btnClass += "bg-blue-600 text-white font-bold shadow-sm";
                } else if (hasNotice) {
                    btnClass += "bg-blue-50 text-blue-600 font-bold border border-blue-200 hover:bg-blue-100";
                } else {
                    btnClass += "text-slate-700 hover:bg-slate-100";
                }

                daysHtml += `<div><button onclick="filterByDate('${dateStr}')" class="${btnClass}">${day}</button></div>`;
            }
            gridEl.innerHTML = daysHtml;
            lucide.createIcons();
        }

        function changeMonth(diff) {
            calMonth += diff;
            if (calMonth > 11) { calMonth = 0; calYear++; }
            else if (calMonth < 0) { calMonth = 11; calYear--; }
            renderCalendar();
        }

        function toggleImportant(id, event) {
            event.stopPropagation();
            const n = notices.find(item => item.id === id);
            if (n) { n.isImportant = !n.isImportant; render(); }
        }

        function renderCard(item) {
            const isImportant = item.isImportant;
            const isNew = item.isNew; // 신규 축적 공고 New 표시
            const dday = item.ntceKindNm === '본공고' ? getDday(item.dateLimit) : null;

            return `
                <div class="bg-white rounded-xl p-5 border ${isImportant ? 'border-amber-400 bg-amber-50/20 gold-glow relative' : 'border-slate-200'} shadow-sm transition flex flex-col justify-between mb-4">
                    <div>
                        <div class="flex justify-between items-start gap-3 mb-2">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs font-semibold px-2 py-0.5 rounded ${item.ntceKindNm === '본공고' ? 'bg-emerald-100 text-emerald-700' : item.ntceKindNm === '사전규격' ? 'bg-purple-100 text-purple-700' : 'bg-indigo-100 text-indigo-700'}">${item.ntceKindNm}</span>
                                ${isNew ? '<span class="text-[10px] font-bold bg-rose-500 text-white px-1.5 py-0.5 rounded animate-pulse">NEW</span>' : ''}
                                ${dday ? `<span class="text-[10px] font-bold bg-blue-600 text-white px-2 py-0.5 rounded-full">${dday}</span>` : ''}
                                <span class="text-xs text-slate-400 font-mono">${item.id}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                ${item.url ? `<a href="${item.url}" target="_blank" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded-md font-medium flex items-center gap-1"><i data-lucide="external-link" class="w-3.5 h-3.5"></i> 원문 링크</a>` : ''}
                                ${currentRole === 'admin' ? `<button onclick="toggleImportant('${item.id}', event)" class="text-xs font-semibold px-2.5 py-1 rounded-md border ${isImportant ? 'bg-amber-100 border-amber-300 text-amber-800' : 'bg-slate-100 border-slate-200 text-slate-600'}"><i data-lucide="star" class="w-3.5 h-3.5 ${isImportant ? 'fill-amber-500 text-amber-500' : ''}"></i> ${isImportant ? '해제' : '지정'}</button>` : ''}
                            </div>
                        </div>
                        <h3 class="text-base font-bold text-slate-900 mb-3">${item.ntceNm}</h3>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                            <div><span class="text-slate-400 block">발주/수요처</span><span class="font-semibold text-slate-700">${item.organ}</span></div>
                            <div><span class="text-slate-400 block">추정용역비</span><span class="font-bold text-blue-600">${formatPrice(item.price)}</span></div>
                            <div><span class="text-slate-400 block">공고일 / 현설일</span><span class="font-medium text-slate-700">${item.dateNotice} / ${item.dateBrief}</span></div>
                            <div><span class="text-slate-400 block">마감일 / 개찰일</span><span class="font-semibold text-rose-600">${item.dateLimit} / ${item.dateOpen}</span></div>
                        </div>
                    </div>
                </div>
            `;
        }

        function render() {
            const container = document.getElementById('notice-container');
            const kw = document.getElementById('search-input').value.toLowerCase();

            let filtered = notices.filter(n => {
                if (selectedDateFilter && n.dateNotice !== selectedDateFilter) return false;
                if (kw && !n.ntceNm.toLowerCase().includes(kw) && !n.organ.toLowerCase().includes(kw)) return false;
                if (currentTab === 'bid') return n.ntceKindNm === '본공고';
                if (currentTab === 'spec') return n.ntceKindNm === '사전규격';
                if (currentTab === 'plan') return n.ntceKindNm === '발주계획';
                return true;
            });

            // 중요 공고 우선, 과거 공고부터 오름차순 정렬
            filtered.sort((a, b) => {
                if (b.isImportant !== a.isImportant) return (b.isImportant ? 1 : 0) - (a.isImportant ? 1 : 0);
                return new Date(a.dateNotice || 0) - new Date(b.dateNotice || 0);
            });

            if (filtered.length === 0) {
                container.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-400 border border-slate-200">조건에 맞는 공고가 없습니다.</div>`;
                lucide.createIcons();
                return;
            }

            if (currentTab === 'all' && !selectedDateFilter) {
                const bids = filtered.filter(n => n.ntceKindNm === '본공고');
                const specs = filtered.filter(n => n.ntceKindNm === '사전규격');
                const plans = filtered.filter(n => n.ntceKindNm === '발주계획');

                container.innerHTML = `
                    <div class="space-y-6">
                        ${bids.length ? `<section class="bg-emerald-50/40 border border-emerald-100 rounded-2xl p-4"><h2 class="text-sm font-bold text-emerald-900 mb-3">🏛️ 본공고 (${bids.length}건)</h2>${bids.map(renderCard).join('')}</section>` : ''}
                        ${specs.length ? `<section class="bg-purple-50/40 border border-purple-100 rounded-2xl p-4"><h2 class="text-sm font-bold text-purple-900 mb-3">🔍 사전규격 (${specs.length}건)</h2>${specs.map(renderCard).join('')}</section>` : ''}
                        ${plans.length ? `<section class="bg-indigo-50/40 border border-indigo-100 rounded-2xl p-4"><h2 class="text-sm font-bold text-indigo-900 mb-3">📌 발주계획 (${plans.length}건)</h2>${plans.map(renderCard).join('')}</section>` : ''}
                    </div>
                `;
            } else {
                container.innerHTML = filtered.map(renderCard).join('');
            }
            lucide.createIcons();
        }

        checkAuth();
    </script>
</body>
</html>
