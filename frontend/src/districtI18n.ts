/** Переводы описаний районов (communities/note) для карточки диаспоры.
 * Ключ — name_en из API. Язык берётся из store. Если района нет — фолбэк на
 * значения из API (они на русском, но UI русский больше не использует). */
import type { Lang } from "./store";

interface Desc { communities: string; note: string; }

export const DISTRICT_I18N: Record<string, Record<Lang, Desc>> = {
  "Academic City / Dubailand Residence": {
    ar: { communities: "تركيبة مختلطة — طلاب ووافدون شباب، سكن ميسور", note: "مجمع جامعات مع سكن؛ متنوع جداً" },
    en: { communities: "Mixed — students and young expats, affordable housing", note: "University cluster with housing; very mixed" },
    es: { communities: "Mixto — estudiantes y jóvenes expatriados, vivienda asequible", note: "Clúster universitario con vivienda; muy mixto" },
  },
  "Al Barsha": {
    ar: { communities: "تركيبة مختلطة — عرب، جنوب آسيويون، فلبينيون، غربيون", note: "منطقة مركزية متعددة الاستخدامات؛ متنوعة جداً" },
    en: { communities: "Mixed — Arabs, South Asians, Filipinos, Westerners", note: "Central mixed-use district; very diverse" },
    es: { communities: "Mixto — árabes, sudasiáticos, filipinos, occidentales", note: "Distrito central de uso mixto; muy diverso" },
  },
  "Al Furjan": {
    ar: { communities: "تركيبة مختلطة — جنوب آسيويون، عرب، غربيون، عائلات", note: "منطقة نامية قرب المترو؛ متنوعة" },
    en: { communities: "Mixed — South Asians, Arabs, Westerners, families", note: "Growing area near the metro; mixed" },
    es: { communities: "Mixto — sudasiáticos, árabes, occidentales, familias", note: "Zona en crecimiento cerca del metro; mixta" },
  },
  "Al Jaddaf": {
    ar: { communities: "تركيبة مختلطة — أبراج جديدة عند الخور، وافدون", note: "منطقة نامية عند الخور؛ متنوعة" },
    en: { communities: "Mixed — new towers by the creek, expats", note: "Developing area by the Creek; mixed" },
    es: { communities: "Mixto — nuevas torres junto al riachuelo, expatriados", note: "Zona en desarrollo junto al Creek; mixta" },
  },
  "Al Karama": {
    ar: { communities: "هنود، فلبينيون، باكستانيون — سكن ميسور وأسواق ومطاعم", note: "منطقة مركزية مكتظة؛ جالية هندية وفلبينية عريقة" },
    en: { communities: "Indians, Filipinos, Pakistanis — affordable housing, markets, restaurants", note: "Dense central district; long-standing Indian and Filipino communities" },
    es: { communities: "Indios, filipinos, pakistaníes — vivienda asequible, mercados, restaurantes", note: "Distrito central denso; comunidades india y filipina de larga data" },
  },
  "Al Khawaneej": {
    ar: { communities: "إماراتيون بشكل رئيسي — فلل واسعة ومزارع", note: "منطقة فلل إماراتية تقليدية" },
    en: { communities: "Predominantly Emiratis — spacious villas, farms", note: "Traditional Emirati villa district" },
    es: { communities: "Predominantemente emiratíes — villas amplias, granjas", note: "Distrito tradicional de villas emiratíes" },
  },
  "Al Nahda": {
    ar: { communities: "هنود وجنوب آسيويون — ميسور، قرب الشارقة، مترو", note: "منطقة مكتظة قرب الشارقة؛ جالية هندية كبيرة" },
    en: { communities: "Indians and South Asians — affordable, near Sharjah, metro", note: "Dense area near Sharjah; large Indian community" },
    es: { communities: "Indios y sudasiáticos — asequible, cerca de Sharjah, metro", note: "Zona densa cerca de Sharjah; gran comunidad india" },
  },
  "Al Quoz": {
    ar: { communities: "تركيبة مختلطة — جنوب آسيويون، عمال، مجمعات فنية", note: "منطقة صناعية سكنية؛ جاليات آسيوية بشكل رئيسي" },
    en: { communities: "Mixed — South Asians, workers, art clusters", note: "Industrial-residential area; mostly Asian communities" },
    es: { communities: "Mixto — sudasiáticos, trabajadores, clústeres de arte", note: "Zona industrial-residencial; comunidades mayormente asiáticas" },
  },
  "Al Qusais": {
    ar: { communities: "جنوب آسيويون، فلبينيون، عرب — ميسور، قرب الشارقة، مترو", note: "منطقة شمالية مكتظة؛ جاليات آسيوية كبيرة" },
    en: { communities: "South Asians, Filipinos, Arabs — affordable, near Sharjah, metro", note: "Dense northern district; large Asian communities" },
    es: { communities: "Sudasiáticos, filipinos, árabes — asequible, cerca de Sharjah, metro", note: "Distrito norte denso; grandes comunidades asiáticas" },
  },
  "Al Rashidiya": {
    ar: { communities: "إماراتيون ووافدون ميسورون — فلل", note: "منطقة ميسورة مختلطة؛ إماراتيون ووافدون" },
    en: { communities: "Emiratis and affluent expats — villas", note: "Well-off mixed district; Emiratis and expats" },
    es: { communities: "Emiratíes y expatriados acomodados — villas", note: "Distrito mixto acomodado; emiratíes y expatriados" },
  },
  "Al Satwa": {
    ar: { communities: "فلبينيون وجنوب آسيويون — منطقة قديمة مدمجة، ميسورة، مركزية", note: "منطقة قديمة منخفضة؛ جالية فلبينية قوية" },
    en: { communities: "Filipinos and South Asians — compact old area, affordable, central", note: "Old low-rise district; strong Filipino community" },
    es: { communities: "Filipinos y sudasiáticos — zona antigua compacta, asequible, céntrica", note: "Distrito antiguo de baja altura; fuerte comunidad filipina" },
  },
  "Al Sufouh": {
    ar: { communities: "وافدون غربيون وميسورون — فلل/شقق قرب مدينة الإعلام", note: "منطقة ساحلية بين مارينا وجميرا؛ وافدون غربيون" },
    en: { communities: "Western and affluent expats — villas/apartments by Media City", note: "Coastal area between Marina and Jumeirah; Western expats" },
    es: { communities: "Expatriados occidentales y acomodados — villas/apartamentos junto a Media City", note: "Zona costera entre Marina y Jumeirah; expatriados occidentales" },
  },
  "Al Warqa": {
    ar: { communities: "مواطنون وعرب ووافدون آسيويون — فلل وشقق", note: "منطقة عائلية هادئة؛ إماراتيون، عرب، آسيويون" },
    en: { communities: "Locals, Arabs and Asian expats — villas and apartments", note: "Quiet family district; Emiratis, Arabs, Asians" },
    es: { communities: "Locales, árabes y expatriados asiáticos — villas y apartamentos", note: "Distrito familiar tranquilo; emiratíes, árabes, asiáticos" },
  },
  "Arabian Ranches": {
    ar: { communities: "عائلات غربية (بريطانية) ووافدون ميسورون — فلل", note: "من أوائل مجتمعات الفلل التمليك؛ عائلات غربية/بريطانية" },
    en: { communities: "Western (British) families and affluent expats — villas", note: "One of the first freehold villa communities; British/Western families" },
    es: { communities: "Familias occidentales (británicas) y expatriados acomodados — villas", note: "Una de las primeras comunidades de villas en propiedad; familias británicas/occidentales" },
  },
  "Arjan": {
    ar: { communities: "تركيبة مختلطة — وافدون ومواطنون، منطقة نامية", note: "منطقة نامية في دبي لاند؛ متنوعة" },
    en: { communities: "Mixed — expats and locals, growing area", note: "Developing Dubailand area; mixed" },
    es: { communities: "Mixto — expatriados y locales, zona en crecimiento", note: "Zona de Dubailand en desarrollo; mixta" },
  },
  "Barsha Heights (Tecom)": {
    ar: { communities: "تركيبة مختلطة — محترفون شباب (قرب مدينة الإعلام/الإنترنت)", note: "منطقة شقق مركزية؛ محترفون شباب، متنوعة" },
    en: { communities: "Mixed — young professionals (near Media/Internet City)", note: "Central apartment district; young professionals, mixed" },
    es: { communities: "Mixto — jóvenes profesionales (cerca de Media/Internet City)", note: "Distrito central de apartamentos; jóvenes profesionales, mixto" },
  },
  "Bluewaters Island": {
    ar: { communities: "وافدون غربيون وميسورون — شقق فاخرة قرب عين دبي", note: "جزيرة اصطناعية قرب JBR؛ وافدون ميسورون" },
    en: { communities: "Western and affluent expats — premium apartments by Ain Dubai", note: "Man-made island by JBR; affluent expats" },
    es: { communities: "Expatriados occidentales y acomodados — apartamentos premium junto a Ain Dubai", note: "Isla artificial junto a JBR; expatriados acomodados" },
  },
  "Bur Dubai": {
    ar: { communities: "هنود، باكستانيون، بنغلاديشيون — مركز تاريخي، سكن ميسور", note: "دبي القديمة؛ جاليات جنوب آسيوية بشكل رئيسي" },
    en: { communities: "Indians, Pakistanis, Bangladeshis — historic center, affordable housing", note: "Old Dubai; predominantly South Asian communities" },
    es: { communities: "Indios, pakistaníes, bangladesíes — centro histórico, vivienda asequible", note: "Dubái antiguo; comunidades predominantemente sudasiáticas" },
  },
  "Business Bay": {
    ar: { communities: "محترفون متعددو الجنسيات — أوروبيون، عرب، هنود، إيرانيون", note: "مركز أعمال عند القناة؛ تركيبة متنوعة جداً" },
    en: { communities: "Multinational professionals — Europeans, Arabs, Indians, Iranians", note: "Business hub by the canal; very mixed" },
    es: { communities: "Profesionales multinacionales — europeos, árabes, indios, iraníes", note: "Centro de negocios junto al canal; muy mixto" },
  },
  "City Walk / Al Wasl": {
    ar: { communities: "تركيبة مختلطة — محترفون شباب، عائلات، وافدون", note: "منطقة حضرية حديثة؛ متنوعة وعائلية" },
    en: { communities: "Mixed — young professionals, families, expats", note: "Modern urban district; mixed, family-friendly" },
    es: { communities: "Mixto — jóvenes profesionales, familias, expatriados", note: "Distrito urbano moderno; mixto, familiar" },
  },
  "Deira": {
    ar: { communities: "هنود، باكستانيون، إيرانيون — أسواق ومتاجر عرقية وسكن ميسور", note: "منطقة تجارية تاريخية؛ جاليات جنوب آسيوية وإيرانية بارزة" },
    en: { communities: "Indians, Pakistanis, Iranians — markets, ethnic shops, affordable housing", note: "Historic trading district; strong South Asian and Iranian diasporas" },
    es: { communities: "Indios, pakistaníes, iraníes — mercados, tiendas étnicas, vivienda asequible", note: "Distrito comercial histórico; fuertes diásporas sudasiática e iraní" },
  },
  "DIFC": {
    ar: { communities: "محترفون ماليون غربيون ودوليون — أبراج فاخرة", note: "المركز المالي؛ محترفون ومستثمرون" },
    en: { communities: "Western and international finance professionals — premium towers", note: "Financial center; professionals and investors" },
    es: { communities: "Profesionales financieros occidentales e internacionales — torres premium", note: "Centro financiero; profesionales e inversores" },
  },
  "Discovery Gardens": {
    ar: { communities: "باكستانيون، بنغلاديشيون، هنود — استوديوهات/شقق ميسورة", note: "بناء اقتصادي؛ جاليات جنوب آسيوية بشكل رئيسي" },
    en: { communities: "Pakistanis, Bangladeshis, Indians — affordable studios/apartments", note: "Budget development; predominantly South Asian communities" },
    es: { communities: "Pakistaníes, bangladesíes, indios — estudios/apartamentos asequibles", note: "Desarrollo económico; comunidades predominantemente sudasiáticas" },
  },
  "Downtown Dubai": {
    ar: { communities: "بريطانيون، أوروبيون، وافدون ناطقون بالروسية — مركز فاخر", note: "المركز الرئيسي (برج خليفة، دبي مول)؛ وافدون ميسورون" },
    en: { communities: "British, Europeans, Russian-speaking expats — premium center", note: "Flagship center (Burj Khalifa, Dubai Mall); affluent expats" },
    es: { communities: "Británicos, europeos, expatriados rusohablantes — centro premium", note: "Centro insignia (Burj Khalifa, Dubai Mall); expatriados acomodados" },
  },
  "Dubai Creek Harbour": {
    ar: { communities: "تركيبة مختلطة — أبراج فاخرة جديدة، وافدون", note: "منطقة ساحلية جديدة؛ متنوعة ونامية" },
    en: { communities: "Mixed — new premium towers, expats", note: "New waterfront district; mixed, growing" },
    es: { communities: "Mixto — nuevas torres premium, expatriados", note: "Nuevo distrito frente al agua; mixto, en crecimiento" },
  },
  "Dubai Festival City": {
    ar: { communities: "تركيبة مختلطة — عائلات ووافدون عند الخور", note: "منطقة متعددة الاستخدامات عند الخور؛ متنوعة" },
    en: { communities: "Mixed — families and expats by the creek", note: "Mixed-use district by the Creek; mixed" },
    es: { communities: "Mixto — familias y expatriados junto al riachuelo", note: "Distrito de uso mixto junto al Creek; mixto" },
  },
  "Dubai Hills Estate": {
    ar: { communities: "عائلات غربية ووافدون ميسورون — فلل وشقق قرب الغولف", note: "منطقة عائلية فاخرة؛ وافدون غربيون" },
    en: { communities: "Western families and affluent expats — villas and apartments by the golf", note: "Premium family district; Western expats" },
    es: { communities: "Familias occidentales y expatriados acomodados — villas y apartamentos junto al golf", note: "Distrito familiar premium; expatriados occidentales" },
  },
  "Dubai Marina": {
    ar: { communities: "بريطانيون، أوروبيون، وافدون ناطقون بالروسية — شقق فاخرة على الماء", note: "موقع مرموق حيوي؛ وافدون غربيون وناطقون بالروسية" },
    en: { communities: "British, Europeans, Russian-speaking expats — premium waterfront apartments", note: "Dynamic prestige location; Western and Russian-speaking expats" },
    es: { communities: "Británicos, europeos, expatriados rusohablantes — apartamentos premium frente al agua", note: "Ubicación prestigiosa dinámica; expatriados occidentales y rusohablantes" },
  },
  "Dubai Production City (IMPZ)": {
    ar: { communities: "تركيبة مختلطة — شقق ميسورة، وافدون", note: "مجمع إعلامي/إنتاجي مع سكن؛ متنوع" },
    en: { communities: "Mixed — affordable apartments, expats", note: "Media/production cluster with housing; mixed" },
    es: { communities: "Mixto — apartamentos asequibles, expatriados", note: "Clúster de medios/producción con vivienda; mixto" },
  },
  "Dubai Silicon Oasis": {
    ar: { communities: "متخصصو تقنية هنود وتركيبة متنوعة جداً — مجمع تقني", note: "مجمع تقني مع سكن؛ من أكثر المناطق تعدداً للجنسيات" },
    en: { communities: "Indian tech professionals and a very mixed makeup — tech cluster", note: "Tech park with housing; one of the most multinational areas" },
    es: { communities: "Profesionales tecnológicos indios y composición muy mixta — clúster tecnológico", note: "Parque tecnológico con vivienda; una de las áreas más multinacionales" },
  },
  "Dubai Sports City": {
    ar: { communities: "تركيبة مختلطة — شقق ميسورة، وافدون شباب", note: "مجمع رياضي (دبي لاند)؛ متنوع، اقتصادي" },
    en: { communities: "Mixed — affordable apartments, young expats", note: "Sports cluster (Dubailand); mixed, budget-friendly" },
    es: { communities: "Mixto — apartamentos asequibles, jóvenes expatriados", note: "Clúster deportivo (Dubailand); mixto, económico" },
  },
  "Emirates Hills": {
    ar: { communities: "أثرياء — إماراتيون، غربيون، نخب عربية وآسيوية", note: "فلل فائقة الفخامة؛ تركيبة ثرية مختلطة" },
    en: { communities: "Affluent — Emiratis, Westerners, Arab and Asian elites", note: "Ultra-premium villas; wealthy mixed makeup" },
    es: { communities: "Acomodados — emiratíes, occidentales, élites árabes y asiáticas", note: "Villas ultra premium; composición adinerada mixta" },
  },
  "Green Community / DIP": {
    ar: { communities: "تركيبة مختلطة — عائلات وافدة، فلل خضراء (مجمع دبي للاستثمار)", note: "منطقة هادئة جنوب غرب؛ متنوعة" },
    en: { communities: "Mixed — expat families, green villas (Dubai Investment Park)", note: "Quiet south-western area; mixed" },
    es: { communities: "Mixto — familias expatriadas, villas verdes (Dubai Investment Park)", note: "Zona tranquila al suroeste; mixta" },
  },
  "International City": {
    ar: { communities: "فلبينيون، صينيون، عرب — سكن رخيص، مجمعات مواضيعية", note: "بناء عنقودي؛ جاليات مختلطة" },
    en: { communities: "Filipinos, Chinese, Arabs — cheap housing, themed clusters", note: "Cluster development; mixed diasporas" },
    es: { communities: "Filipinos, chinos, árabes — vivienda barata, clústeres temáticos", note: "Desarrollo por clústeres; diásporas mixtas" },
  },
  "Jumeirah": {
    ar: { communities: "مواطنو الإمارات ووافدون ميسورون — بناء فلل", note: "منطقة فلل مرموقة؛ مواطنون ووافدون ميسورون" },
    en: { communities: "Emiratis and affluent expats — villa development", note: "Prestigious villa district; Emiratis and well-off expats" },
    es: { communities: "Emiratíes y expatriados acomodados — desarrollo de villas", note: "Distrito de villas prestigioso; emiratíes y expatriados acomodados" },
  },
  "Jumeirah Beach Residence (JBR)": {
    ar: { communities: "بريطانيون، أوروبيون، وافدون ناطقون بالروسية — سكن على الشاطئ", note: "موقع شاطئي مرموق؛ وافدون غربيون وناطقون بالروسية" },
    en: { communities: "British, Europeans, Russian-speaking expats — beachfront housing", note: "Prestige beach location; Western and Russian-speaking expats" },
    es: { communities: "Británicos, europeos, expatriados rusohablantes — viviendas frente a la playa", note: "Ubicación de playa prestigiosa; expatriados occidentales y rusohablantes" },
  },
  "Jumeirah Golf Estates": {
    ar: { communities: "عائلات وافدة غربية — فلل قرب ملاعب الغولف", note: "مجتمع غولف تمليك؛ وافدون غربيون" },
    en: { communities: "Western expat families — villas by the golf courses", note: "Freehold golf community; Western expats" },
    es: { communities: "Familias expatriadas occidentales — villas junto a los campos de golf", note: "Comunidad de golf en propiedad; expatriados occidentales" },
  },
  "Jumeirah Islands": {
    ar: { communities: "وافدون غربيون وميسورون — فلل على جزر صغيرة", note: "جيب فلل فاخر؛ وافدون غربيون" },
    en: { communities: "Western and affluent expats — villas on small islands", note: "Premium villa enclave; Western expats" },
    es: { communities: "Expatriados occidentales y acomodados — villas en islas pequeñas", note: "Enclave de villas premium; expatriados occidentales" },
  },
  "Jumeirah Lakes Towers (JLT)": {
    ar: { communities: "محترفون غربيون وناطقون بالروسية وهنود — أبراج عند البحيرات", note: "منطقة شقق تجارية قرب مارينا؛ كثير من الوافدين المحترفين" },
    en: { communities: "Western, Russian-speaking and Indian professionals — towers by the lakes", note: "Business apartment district next to Marina; many professional expats" },
    es: { communities: "Profesionales occidentales, rusohablantes e indios — torres junto a los lagos", note: "Distrito de apartamentos de negocios junto a Marina; muchos expatriados profesionales" },
  },
  "Jumeirah Village Circle (JVC)": {
    ar: { communities: "عائلات هندية وجاليات مختلطة — شقق وتاون هاوس ميسورة", note: "محبوب لدى العائلات الهندية (مدارس، حدائق)؛ سكن ميسور" },
    en: { communities: "Indian families and mixed communities — affordable apartments and townhouses", note: "Popular with Indian families (schools, parks); affordable housing" },
    es: { communities: "Familias indias y comunidades mixtas — apartamentos y townhouses asequibles", note: "Popular entre familias indias (colegios, parques); vivienda asequible" },
  },
  "Jumeirah Village Triangle (JVT)": {
    ar: { communities: "تركيبة مختلطة — فلل وتاون هاوس ميسورة", note: "مجتمع عائلي ميسور؛ متنوع" },
    en: { communities: "Mixed — affordable villas and townhouses", note: "Affordable family community; mixed" },
    es: { communities: "Mixto — villas y townhouses asequibles", note: "Comunidad familiar asequible; mixta" },
  },
  "Liwan": {
    ar: { communities: "تركيبة مختلطة — شقق ميسورة، وافدون", note: "منطقة دبي لاند ميسورة؛ متنوعة" },
    en: { communities: "Mixed — affordable apartments, expats", note: "Affordable Dubailand area; mixed" },
    es: { communities: "Mixto — apartamentos asequibles, expatriados", note: "Zona asequible de Dubailand; mixta" },
  },
  "Meydan / MBR City": {
    ar: { communities: "إماراتيون ووافدون ميسورون — فلل/شقق فاخرة جديدة", note: "منطقة فاخرة جديدة قرب الميدان؛ ميسورة" },
    en: { communities: "Emiratis and affluent expats — new premium villas/apartments", note: "New premium district by the racecourse; affluent" },
    es: { communities: "Emiratíes y expatriados acomodados — nuevas villas/apartamentos premium", note: "Nuevo distrito premium junto al hipódromo; acomodado" },
  },
  "Mirdif": {
    ar: { communities: "مواطنون، عائلات عربية ووافدون غربيون — فلل، منطقة عائلية", note: "منطقة عائلية منخفضة؛ إماراتيون، عرب، وافدون غربيون" },
    en: { communities: "Locals, Arab families and Western expats — villas, family area", note: "Low-rise family district; Emiratis, Arabs, Western expats" },
    es: { communities: "Locales, familias árabes y expatriados occidentales — villas, zona familiar", note: "Distrito familiar de baja altura; emiratíes, árabes, expatriados occidentales" },
  },
  "Motor City": {
    ar: { communities: "تركيبة مختلطة — عائلات وعزّاب، دون جنسية مهيمنة", note: "منطقة عائلية ميسورة (دبي لاند)؛ متنوعة جداً" },
    en: { communities: "Mixed — families and singles, no dominant nationality", note: "Affordable family district (Dubailand); very mixed" },
    es: { communities: "Mixto — familias y solteros, sin nacionalidad dominante", note: "Distrito familiar asequible (Dubailand); muy mixto" },
  },
  "Mudon": {
    ar: { communities: "تركيبة مختلطة — فلل/تاون هاوس، عائلات", note: "مجتمع فلل عائلي (دبي لاند)؛ متنوع" },
    en: { communities: "Mixed — villas/townhouses, families", note: "Family villa community (Dubailand); mixed" },
    es: { communities: "Mixto — villas/townhouses, familias", note: "Comunidad familiar de villas (Dubailand); mixta" },
  },
  "Muhaisnah": {
    ar: { communities: "جنوب آسيويون (منهم عمال سونابور)، عرب — أكثر المناطق سكاناً", note: "أكثر مجتمعات دبي سكاناً (~235 ألف)؛ جنوب آسيوي" },
    en: { communities: "South Asians (incl. Sonapur workers), Arabs — most populous district", note: "Dubai's most populous community (~235k); South Asian" },
    es: { communities: "Sudasiáticos (incl. trabajadores de Sonapur), árabes — distrito más poblado", note: "La comunidad más poblada de Dubái (~235 mil); sudasiática" },
  },
  "Nad Al Sheba": {
    ar: { communities: "إماراتيون ووافدون ميسورون — فلل قرب الميدان", note: "منطقة فلل إماراتية قرب الميدان" },
    en: { communities: "Emiratis and affluent expats — villas near Meydan", note: "Emirati villa district next to Meydan" },
    es: { communities: "Emiratíes y expatriados acomodados — villas cerca de Meydan", note: "Distrito de villas emiratíes junto a Meydan" },
  },
  "Oud Metha / Umm Hurair": {
    ar: { communities: "هنود وجنوب آسيويون — منطقة راسخة، مدارس، مستشفيات", note: "منطقة مركزية قرب بر دبي؛ جاليات جنوب آسيوية" },
    en: { communities: "Indians and South Asians — established area, schools, hospitals", note: "Central area near Bur Dubai; South Asian communities" },
    es: { communities: "Indios y sudasiáticos — zona consolidada, colegios, hospitales", note: "Zona central cerca de Bur Dubai; comunidades sudasiáticas" },
  },
  "Palm Jumeirah": {
    ar: { communities: "مواطنون ووافدون ميسورون — فلل وشقق فاخرة", note: "جزيرة اصطناعية؛ عقارات فاخرة" },
    en: { communities: "Emiratis and affluent expats — villas and premium apartments", note: "Man-made island; premium real estate" },
    es: { communities: "Emiratíes y expatriados acomodados — villas y apartamentos premium", note: "Isla artificial; inmuebles premium" },
  },
  "The Greens / The Views": {
    ar: { communities: "محترفون ووافدون غربيون — مجمعات شقق خضراء", note: "منطقة شقق هادئة؛ وافدون غربيون بشكل رئيسي" },
    en: { communities: "Western professionals and expats — green apartment complexes", note: "Quiet apartment district; predominantly Western expats" },
    es: { communities: "Profesionales y expatriados occidentales — complejos de apartamentos verdes", note: "Distrito de apartamentos tranquilo; predominantemente expatriados occidentales" },
  },
  "The Springs / Meadows": {
    ar: { communities: "عائلات غربية (بريطانية) — تاون هاوس وفلل (Emirates Living)", note: "حزام فلل عائلي؛ وافدون غربيون بشكل رئيسي" },
    en: { communities: "Western (British) families — townhouses and villas (Emirates Living)", note: "Family villa belt; predominantly Western expats" },
    es: { communities: "Familias occidentales (británicas) — townhouses y villas (Emirates Living)", note: "Cinturón de villas familiar; predominantemente expatriados occidentales" },
  },
  "Town Square (Nshama)": {
    ar: { communities: "تركيبة مختلطة — شقق وتاون هاوس ميسورة، عائلات شابة", note: "مجتمع عائلي اقتصادي؛ متنوع" },
    en: { communities: "Mixed — affordable apartments and townhouses, young families", note: "Budget family community; mixed" },
    es: { communities: "Mixto — apartamentos y townhouses asequibles, familias jóvenes", note: "Comunidad familiar económica; mixta" },
  },
  "Umm Suqeim": {
    ar: { communities: "إماراتيون ووافدون ميسورون — فلل قرب الساحل", note: "منطقة فلل ساحلية؛ إماراتيون ووافدون ميسورون" },
    en: { communities: "Emiratis and affluent expats — villas near the coast", note: "Coastal villa district; Emiratis and well-off expats" },
    es: { communities: "Emiratíes y expatriados acomodados — villas cerca de la costa", note: "Distrito de villas costero; emiratíes y expatriados acomodados" },
  },
  "Za'abeel": {
    ar: { communities: "إماراتيون ومؤسسات حكومية — فلل، منطقة قصور", note: "منطقة إماراتية مركزية قرب وسط المدينة" },
    en: { communities: "Emiratis and government institutions — villas, palace zone", note: "Central Emirati district next to Downtown" },
    es: { communities: "Emiratíes e instituciones gubernamentales — villas, zona de palacios", note: "Distrito emiratí central junto a Downtown" },
  },
};

export function districtDesc(name: string, lang: Lang): Desc | null {
  return DISTRICT_I18N[name]?.[lang] ?? null;
}
