// 메타 광고 라이브러리 추출기 — 브라우저 콘솔에 붙여넣고 SCAN(브랜드정규식) 실행
//
// 사용법
//   1. https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=KR&q=브랜드명&search_type=keyword_unordered
//   2. F12 콘솔에 이 파일 전체를 붙여넣는다
//   3. await SCAN(/이니스프리|innisfree/i)
//
// ⚠ 한계
//   - 로그아웃 상태에서는 24~30건까지만 로드된다. 로그인하면 더 깊이 볼 수 있다
//   - `결과 ~N개`는 키워드가 들어간 모든 광고다. 자사 광고가 아니다.
//     반드시 advTop을 확인해 오염 정도를 보고, own/loaded 비율로 보정할 것
//   - 클래스명이 난독화되어 있어 DOM 셀렉터 대신 innerText 파싱을 쓴다.
//     메타가 문구("라이브러리 ID:", "광고 상세 정보 보기")를 바꾸면 깨진다

window.SCAN = async function (BRAND, rounds) {
  const C = {
    브랜드서사: /창립|철학|자연주의|산지|재배|농장|밭에서|헤리티지|브랜드\s*필름|since\s*\d|년의\s*연구|장인|제주|울릉|독도|자연에서/i,
    성분효능: /성분|히알루론|레티놀|시카|나이아신|세라마이드|판테놀|비타민|콜라겐|펩타이드|앰플|보습|수분|진정|모공|주름|미백|탄력|각질|트러블|자외선|SPF/i,
    할인가격: /할인|특가|세일|쿠폰|증정|1\+1|최대\s*\d+%|\d+%\s*할인|무료배송|단독가/i,
    유통채널: /올리브영|올영|무신사|쿠팡|네이버|지마켓|11번가|무뷰페|지그재그/i,
    순위리뷰: /1등|no\.?\s*1|1위|리뷰\s*[\d만천]|재구매|랭킹|베스트|판매량/i,
    콜라보: /콜라보|앰버서더|모델|아이돌/i,
  };

  // 무한 스크롤 로드
  for (let i = 0; i < (rounds || 6); i++) {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise((r) => setTimeout(r, 1200));
  }

  const t = document.body.innerText;
  const total = (t.match(/결과\s*~?\s*([\d,]+)\s*개/) || [])[1] || null;

  const seen = new Set();
  const ads = t
    .split(/라이브러리 ID:\s*/)
    .slice(1)
    .map((p) => {
      const id = (p.match(/^(\d+)/) || [])[1];
      const start =
        (p.match(/(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*에 게재 시작/) || [])
          .slice(1)
          .join('-') || null;
      // "광고 N개에서 이 크리에이티브 및 문구를 사용합니다" = 같은 소재의 중복 집행 수
      const dup = parseInt((p.match(/광고\s*(\d+)개에서 이 크리에이티브/) || [])[1] || '1', 10);
      const m = p.match(/(?:광고 상세 정보 보기|요약 세부 사항 보기)\n([^\n]+)\n광고\n([\s\S]*)/);
      let copy = m ? m[2] : '';
      // 다음 카드의 머리말이 붙어 오므로 상태 표시에서 자른다
      copy = copy.split(/\n​\n(?:활성|비활성)/)[0].replace(/\n0:00 \/ [\d:]+/, '').trim();
      return { id, start, dup, adv: m ? m[1].trim() : null, copy };
    })
    .filter((a) => a.id && !seen.has(a.id) && seen.add(a.id));

  const own = ads.filter((a) => a.adv && BRAND.test(a.adv));
  const cls = {};
  for (const k in C) cls[k] = own.filter((a) => C[k].test(a.copy)).length;

  const ac = {};
  ads.forEach((a) => (ac[a.adv] = (ac[a.adv] || 0) + 1));

  return {
    total,                                   // 검색 결과 총계 (타사 광고 포함)
    loaded: ads.length,                      // 실제 로드된 표본
    own: own.length,                         // 표본 중 자사 광고
    추정자사물량: total ? Math.round(total * (own.length / ads.length)) : null,
    creatives: own.reduce((s, a) => s + a.dup, 0),
    cls,
    advTop: Object.entries(ac).sort((a, b) => b[1] - a[1]).slice(0, 6),
    ads: own,                                // 자사 광고 전체 (카피 포함)
  };
};

console.log('준비됨. 예) await SCAN(/이니스프리|innisfree/i)');
