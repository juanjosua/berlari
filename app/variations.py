"""Workout variations and bodyweight strength routines: what each one is, step-by-step how to do it,
and the heart-rate zone it should be done in. Texts are (English, Indonesian). Pure data + rendering.

Placeholders in step texts are filled per athlete: {easy_hr} {hard_hr} {tempo_hr} {walk_hr} (bpm ranges,
or % of max HR when max HR is unknown) and {easy_pace} {tempo_pace} {int_pace} {race_pace}.
Only variations whose structure can be seen in Strava data (speed and heart-rate samples) are listed."""

# Heart-rate zones as fractions of max HR.
Z_WALK, Z_EASY, Z_LONG, Z_TEMPO, Z_HARD = (0.55, 0.70), (0.60, 0.75), (0.65, 0.78), (0.80, 0.88), (0.85, 0.95)

V = {
    "EASY": [
        {"id": "aerobic", "acts": "run", "zone": Z_EASY,
         "label": ("Steady aerobic run", "Lari aerobik stabil"),
         "what": ("The everyday easy run: slow enough to talk in full sentences the whole time. It builds the "
                  "heart, blood vessels and endurance without tiring you for the next hard day.",
                  "Lari santai harian: cukup pelan sampai kamu bisa bicara kalimat utuh sepanjang lari. Membangun "
                  "jantung, pembuluh darah dan daya tahan tanpa membuatmu lelah untuk latihan berat berikutnya."),
         "how": [("Run the whole distance at an even, relaxed pace (around {easy_pace}).",
                  "Lari seluruh jarak dengan pace rata dan rileks (sekitar {easy_pace})."),
                 ("Keep heart rate in {easy_hr}. If it climbs higher, slow down or walk a little.",
                  "Jaga detak jantung di {easy_hr}. Kalau naik lebih tinggi, pelankan atau jalan sebentar.")]},
        {"id": "runwalk", "acts": "runwalk", "zone": Z_EASY,
         "label": ("Run-walk", "Lari-jalan"),
         "what": ("Alternate easy jogging with brisk walking. You cover more time on your feet with less impact, "
                  "which is ideal while joints and tendons are still getting used to running.",
                  "Bergantian jogging santai dan jalan cepat. Kamu bisa bergerak lebih lama dengan benturan lebih "
                  "ringan, ideal selama sendi dan tendon masih beradaptasi dengan lari."),
         "how": [("Jog easily for 2–3 minutes, then walk briskly for 1–2 minutes. Repeat for the whole session.",
                  "Jogging santai 2–3 menit, lalu jalan cepat 1–2 menit. Ulangi sepanjang sesi."),
                 ("Keep heart rate in {easy_hr} during the jog parts; the walks let it come down.",
                  "Jaga detak jantung di {easy_hr} saat jogging; bagian jalan membuatnya turun lagi."),
                 ("As it gets easier over the weeks, jog longer and walk shorter (e.g. 3 min jog / 1 min walk).",
                  "Saat makin mudah dari minggu ke minggu, perpanjang jogging dan perpendek jalan (mis. 3 menit jogging / 1 menit jalan).")]},
        {"id": "walk", "acts": "walk", "zone": Z_WALK,
         "label": ("Brisk walk", "Jalan cepat"),
         "what": ("A fast, purposeful walk. Very low impact, good for recovery days or when starting from zero.",
                  "Jalan cepat dan mantap. Benturannya sangat ringan, cocok untuk hari pemulihan atau saat mulai dari nol."),
         "how": [("Walk fast enough that you breathe a bit harder but can still talk easily.",
                  "Jalan cukup cepat sampai napas sedikit lebih berat tapi masih bisa bicara dengan mudah."),
                 ("Keep heart rate in {walk_hr}. Record it on Strava as a Walk.",
                  "Jaga detak jantung di {walk_hr}. Catat di Strava sebagai Walk.")]},
        {"id": "recovery", "acts": "run", "zone": (0.55, 0.72),
         "label": ("Recovery run", "Lari pemulihan"),
         "what": ("A short, very slow run the day after a hard session. It feels almost too slow, and that's the "
                  "point: blood flow helps the legs recover without adding stress.",
                  "Lari pendek dan sangat pelan sehari setelah sesi berat. Rasanya hampir terlalu pelan, dan memang "
                  "begitu tujuannya: aliran darah membantu kaki pulih tanpa menambah beban."),
         "how": [("Run 20–40 minutes, slower than your normal easy pace.",
                  "Lari 20–40 menit, lebih pelan dari pace santai biasa."),
                 ("Keep heart rate below {recovery_top}. Walk if needed.",
                  "Jaga detak jantung di bawah {recovery_top}. Jalan kalau perlu.")]},
        {"id": "strides", "acts": "run", "zone": Z_EASY,
         "label": ("Easy run + strides", "Lari santai + strides"),
         "what": ("An easy run finished with short, fast but relaxed accelerations called strides. They teach your "
                  "legs to move quickly and smoothly without making you tired.",
                  "Lari santai yang diakhiri akselerasi pendek, cepat tapi rileks, yang disebut strides. Melatih "
                  "kaki bergerak cepat dan luwes tanpa membuat lelah."),
         "how": [("Run easy for most of the session (heart rate {easy_hr}).",
                  "Lari santai hampir seluruh sesi (detak jantung {easy_hr})."),
                 ("At the end, do 6 strides: speed up over 20 seconds to about 90% effort, staying relaxed (not a sprint).",
                  "Di akhir, lakukan 6 strides: percepat selama 20 detik sampai sekitar 90% usaha, tetap rileks (bukan sprint)."),
                 ("Walk or jog 60 seconds between strides so each one feels fresh.",
                  "Jalan atau jogging 60 detik di antara strides supaya tiap strides terasa segar.")]},
        {"id": "progression", "acts": "run", "zone": (0.60, 0.80),
         "label": ("Progression easy run", "Lari santai progresif"),
         "what": ("An easy run that starts very slowly and ends a little quicker. Good on days when your legs feel stiff.",
                  "Lari santai yang dimulai sangat pelan dan berakhir sedikit lebih cepat. Cocok saat kaki terasa kaku."),
         "how": [("First third: very easy, slower than {easy_pace}.", "Sepertiga awal: sangat santai, lebih pelan dari {easy_pace}."),
                 ("Middle third: your normal easy pace.", "Sepertiga tengah: pace santai biasa."),
                 ("Last third: a bit quicker, still able to talk (heart rate up to the top of {easy_hr}).",
                  "Sepertiga akhir: sedikit lebih cepat, masih bisa bicara (detak jantung sampai batas atas {easy_hr}).")]},
        {"id": "trail", "acts": "run", "zone": Z_EASY,
         "label": ("Trail / soft-surface run", "Lari trail / permukaan lunak"),
         "what": ("An easy run on dirt, grass or hilly trails. Softer ground is kinder to joints and strengthens "
                  "feet and ankles. Pace doesn't matter here, effort does.",
                  "Lari santai di tanah, rumput atau jalur berbukit. Permukaan lunak lebih ramah sendi dan menguatkan "
                  "kaki serta pergelangan. Pace tidak penting di sini, yang penting usaha."),
         "how": [("Choose a trail, park or rolling route and run by feel, not by pace.",
                  "Pilih jalur trail, taman atau rute bergelombang dan lari sesuai rasa, bukan pace."),
                 ("Keep heart rate in {easy_hr}; walk the steep uphills. Record as Trail Run if you can.",
                  "Jaga detak jantung di {easy_hr}; jalan saja di tanjakan curam. Catat sebagai Trail Run kalau bisa.")]},
    ],
    "LONG": [
        {"id": "classic", "acts": "run", "zone": Z_LONG,
         "label": ("Classic easy long run", "Lari jauh santai klasik"),
         "what": ("The week's longest run at a comfortable, conversational pace. It builds endurance, strengthens "
                  "tendons and teaches your body to use fat for fuel.",
                  "Lari terpanjang minggu ini dengan pace nyaman sambil bisa ngobrol. Membangun daya tahan, "
                  "menguatkan tendon dan melatih tubuh memakai lemak sebagai bahan bakar."),
         "how": [("Run the whole distance at an even, easy pace (around {easy_pace}).",
                  "Lari seluruh jarak dengan pace rata dan santai (sekitar {easy_pace})."),
                 ("Keep heart rate in {long_hr}. Drink every 30–40 minutes on runs over an hour.",
                  "Jaga detak jantung di {long_hr}. Minum tiap 30–40 menit untuk lari lebih dari satu jam.")]},
        {"id": "walk_breaks", "acts": "runwalk", "zone": Z_LONG,
         "label": ("Long run with walk breaks", "Lari jauh dengan jeda jalan"),
         "what": ("The long run with short planned walks. Walking before you're tired lets you go further with "
                  "less strain, and many runners use it on race day too.",
                  "Lari jauh dengan jeda jalan singkat yang direncanakan. Berjalan sebelum lelah membuatmu bisa lebih "
                  "jauh dengan beban lebih ringan, dan banyak pelari memakainya juga saat lomba."),
         "how": [("Run easily (heart rate {long_hr}) and walk 30–60 seconds every 2 km, or every 8–10 minutes.",
                  "Lari santai (detak jantung {long_hr}) dan jalan 30–60 detik tiap 2 km, atau tiap 8–10 menit."),
                 ("Walk briskly during the breaks, then start running again before you feel rested.",
                  "Jalan cepat saat jeda, lalu mulai lari lagi sebelum merasa benar-benar pulih."),
                 ("Practise drinking during the walk breaks.", "Latih minum saat jeda jalan.")]},
        {"id": "progression", "acts": "run", "zone": (0.65, 0.85),
         "label": ("Progression long run", "Lari jauh progresif"),
         "what": ("A long run that starts easy and gets faster bit by bit. It teaches you to push when your legs are "
                  "already tired, like the second half of a race.",
                  "Lari jauh yang dimulai santai dan makin cepat sedikit demi sedikit. Melatihmu tetap mendorong saat "
                  "kaki sudah lelah, seperti paruh kedua lomba."),
         "how": [("First half: easy (heart rate {long_hr}).", "Paruh pertama: santai (detak jantung {long_hr})."),
                 ("Then speed up a little every 2–3 km.", "Lalu percepat sedikit tiap 2–3 km."),
                 ("Last quarter: steady, close to race pace ({race_pace}), never all-out.",
                  "Seperempat akhir: stabil, mendekati pace lomba ({race_pace}), jangan habis-habisan.")]},
        {"id": "fast_finish", "acts": "run", "zone": (0.65, 0.88),
         "label": ("Fast-finish long run", "Lari jauh fast finish"),
         "what": ("Mostly easy, but the final 15–20 minutes are run at tempo effort. It trains you to hold a strong "
                  "pace late in a race when you're running low on energy.",
                  "Sebagian besar santai, tapi 15–20 menit terakhir di usaha tempo. Melatihmu menahan pace kuat di "
                  "akhir lomba saat energi mulai menipis."),
         "how": [("Run easy (heart rate {long_hr}) for most of the distance.",
                  "Lari santai (detak jantung {long_hr}) hampir seluruh jarak."),
                 ("For the last 15–20 minutes, switch to tempo pace ({tempo_pace}, heart rate {tempo_hr}): "
                  "comfortably hard, you can only say a few words.",
                  "Untuk 15–20 menit terakhir, ganti ke pace tempo ({tempo_pace}, detak jantung {tempo_hr}): "
                  "berat tapi terkendali, hanya bisa bicara beberapa kata.")]},
        {"id": "race_pace", "acts": "run", "zone": (0.65, 0.88),
         "label": ("Long run with race-pace blocks", "Lari jauh dengan blok pace lomba"),
         "what": ("An easy long run with two longer stretches at your goal race pace. You practise the exact pace "
                  "and drinking you'll use on race day.",
                  "Lari jauh santai dengan dua bagian panjang di pace target lomba. Kamu berlatih pace dan cara minum "
                  "yang persis akan dipakai saat lomba."),
         "how": [("Run the first half easy (heart rate {long_hr}).", "Lari paruh pertama dengan santai (detak jantung {long_hr})."),
                 ("Then run 15 minutes at goal race pace ({race_pace}), 5 minutes easy, and another 15 minutes at race pace.",
                  "Lalu lari 15 menit di pace target lomba ({race_pace}), 5 menit santai, dan 15 menit lagi di pace lomba."),
                 ("Finish the rest easy.", "Selesaikan sisanya dengan santai.")]},
        {"id": "surges", "acts": "run", "zone": (0.65, 0.90),
         "label": ("Long run with surges", "Lari jauh dengan akselerasi"),
         "what": ("An easy long run with a few short pickups. It keeps the run interesting and practises changing "
                  "pace on tired legs, like passing someone in a race.",
                  "Lari jauh santai dengan beberapa akselerasi pendek. Membuat lari tidak membosankan dan melatih "
                  "perubahan pace dengan kaki lelah, seperti menyalip orang saat lomba."),
         "how": [("Run easy (heart rate {long_hr}).", "Lari santai (detak jantung {long_hr})."),
                 ("In the second half, 6 times: speed up for 1–2 minutes to a hard-but-controlled effort, then "
                  "settle back to easy for at least 5 minutes.",
                  "Di paruh kedua, 6 kali: percepat 1–2 menit sampai usaha berat tapi terkendali, lalu kembali santai "
                  "minimal 5 menit.")]},
        {"id": "hilly", "acts": "run", "zone": (0.65, 0.82),
         "label": ("Hilly / trail long run", "Lari jauh berbukit / trail"),
         "what": ("A long run on a hilly or trail route, run by effort instead of pace. Climbs and descents build "
                  "leg strength and joint stability.",
                  "Lari jauh di rute berbukit atau trail, dengan patokan usaha, bukan pace. Tanjakan dan turunan "
                  "membangun kekuatan kaki dan stabilitas sendi."),
         "how": [("Pick a route with at least 10 m of climbing per km.",
                  "Pilih rute dengan tanjakan minimal 10 m per km."),
                 ("Keep the effort easy (heart rate {long_hr}): slow down uphill, walk steep parts, "
                  "take short quick steps downhill.",
                  "Jaga usaha tetap santai (detak jantung {long_hr}): pelankan di tanjakan, jalan di bagian curam, "
                  "langkah pendek dan cepat saat turunan.")]},
    ],
    "TEMPO": [
        {"id": "steady", "acts": "run", "zone": Z_TEMPO,
         "label": ("Steady tempo run", "Lari tempo stabil"),
         "what": ("20–30 minutes non-stop at 'comfortably hard' effort, roughly the pace you could hold for an "
                  "hour. It raises the speed you can sustain before getting exhausted.",
                  "20–30 menit nonstop di usaha 'berat tapi nyaman', kira-kira pace yang bisa kamu tahan selama satu "
                  "jam. Meningkatkan kecepatan yang bisa dipertahankan sebelum kelelahan."),
         "how": [("Warm up: 10 minutes easy jog.", "Pemanasan: 10 menit jogging santai."),
                 ("Main part: 20–30 minutes at tempo pace ({tempo_pace}), heart rate {tempo_hr}. "
                  "You can say a few words, not full sentences.",
                  "Inti: 20–30 menit di pace tempo ({tempo_pace}), detak jantung {tempo_hr}. "
                  "Kamu bisa bicara beberapa kata, bukan kalimat utuh."),
                 ("Cool down: 10 minutes easy jog or walk.", "Pendinginan: 10 menit jogging santai atau jalan.")]},
        {"id": "cruise", "acts": "run", "zone": Z_TEMPO,
         "label": ("Cruise intervals", "Cruise interval"),
         "what": ("Tempo running split into chunks with short jogs between. You get the same benefit as a steady "
                  "tempo but it feels easier, so you can do more of it.",
                  "Lari tempo yang dipecah menjadi beberapa bagian dengan jogging singkat di antaranya. Manfaatnya "
                  "sama dengan tempo stabil tapi terasa lebih ringan, jadi bisa lebih banyak."),
         "how": [("Warm up: 10 minutes easy jog.", "Pemanasan: 10 menit jogging santai."),
                 ("Run 1 km at tempo pace ({tempo_pace}, heart rate {tempo_hr}), then jog easily for 60 seconds.",
                  "Lari 1 km di pace tempo ({tempo_pace}, detak jantung {tempo_hr}), lalu jogging santai 60 detik."),
                 ("Repeat 4–5 times.", "Ulangi 4–5 kali."),
                 ("Cool down: 10 minutes easy.", "Pendinginan: 10 menit santai.")]},
        {"id": "progressive", "acts": "run", "zone": (0.70, 0.88),
         "label": ("Progressive tempo run", "Lari tempo progresif"),
         "what": ("Starts at an easy-moderate pace and builds up so the last 15 minutes are at tempo effort. "
                  "It teaches you to finish strong (a 'negative split').",
                  "Dimulai di pace santai-sedang lalu meningkat sehingga 15 menit terakhir di usaha tempo. Melatihmu "
                  "selesai dengan kuat ('negative split')."),
         "how": [("First 10–15 minutes: easy.", "10–15 menit pertama: santai."),
                 ("Next 10 minutes: steady, a little faster.", "10 menit berikutnya: stabil, sedikit lebih cepat."),
                 ("Last 15 minutes: tempo pace ({tempo_pace}) or slightly faster, heart rate {tempo_hr}.",
                  "15 menit terakhir: pace tempo ({tempo_pace}) atau sedikit lebih cepat, detak jantung {tempo_hr}."),
                 ("Cool down 5–10 minutes easy.", "Pendinginan 5–10 menit santai.")]},
    ],
    "INT": [
        {"id": "n4x4", "acts": "run", "zone": Z_HARD,
         "label": ("Norwegian 4x4", "Norwegian 4x4"),
         "what": ("Four 4-minute hard efforts with 3 minutes easy between. One of the most effective sessions for "
                  "raising VO2max (how much oxygen your body can use) and it works at any pace, even uphill walking.",
                  "Empat kali usaha berat 4 menit dengan 3 menit santai di antaranya. Salah satu sesi paling efektif "
                  "untuk menaikkan VO2max (berapa banyak oksigen yang bisa dipakai tubuh) dan cocok untuk pace apa pun, "
                  "bahkan jalan menanjak."),
         "how": [("Warm up: 10 minutes easy jog or brisk walk.", "Pemanasan: 10 menit jogging santai atau jalan cepat."),
                 ("4 minutes hard: heart rate {hard_hr}. Breathing is heavy; you can't talk.",
                  "4 menit berat: detak jantung {hard_hr}. Napas berat; tidak bisa bicara."),
                 ("3 minutes easy jog or walk, letting heart rate drop toward {easy_hr}.",
                  "3 menit jogging santai atau jalan, biarkan detak jantung turun ke arah {easy_hr}."),
                 ("Repeat 4 times in total, then 10 minutes easy to cool down.",
                  "Ulangi total 4 kali, lalu 10 menit santai untuk pendinginan.")]},
        {"id": "track", "acts": "run", "zone": Z_HARD,
         "label": ("Classic 800 m repeats", "Repetisi 800 m klasik"),
         "what": ("The classic speed session: run 800 metres (two laps of a running track) fast, recover, repeat. "
                  "It builds speed and teaches you to run fast with good form.",
                  "Sesi kecepatan klasik: lari 800 meter (dua putaran lintasan atletik) dengan cepat, pulih, ulangi. "
                  "Membangun kecepatan dan melatih lari cepat dengan teknik yang baik."),
         "how": [("Warm up: 10–15 minutes easy jog.", "Pemanasan: 10–15 menit jogging santai."),
                 ("Run 800 m at interval pace ({int_pace}); it takes about 3–4 minutes. Heart rate climbs to {hard_hr}.",
                  "Lari 800 m di pace interval ({int_pace}); sekitar 3–4 menit. Detak jantung naik ke {hard_hr}."),
                 ("Jog easily for 2–3 minutes (or 400 m) to recover.", "Jogging santai 2–3 menit (atau 400 m) untuk pulih."),
                 ("Repeat 6 times, then cool down 10 minutes easy.", "Ulangi 6 kali, lalu pendinginan 10 menit santai.")]},
        {"id": "hiit", "acts": "run", "zone": Z_HARD,
         "label": ("HIIT 30/30", "HIIT 30/30"),
         "what": ("High-intensity interval training: 30 seconds fast, 30 seconds slow, many times. The short "
                  "efforts let you spend a lot of time at high intensity without exhausting yourself.",
                  "High-intensity interval training: 30 detik cepat, 30 detik pelan, berkali-kali. Usaha yang pendek "
                  "membuatmu bisa lama di intensitas tinggi tanpa kehabisan tenaga."),
         "how": [("Warm up: 10 minutes easy jog.", "Pemanasan: 10 menit jogging santai."),
                 ("30 seconds fast (about your 5K race effort, faster than {tempo_pace}).",
                  "30 detik cepat (sekitar usaha lomba 5K, lebih cepat dari {tempo_pace})."),
                 ("30 seconds slow jog (or walk if you need to).", "30 detik jogging pelan (atau jalan kalau perlu)."),
                 ("Repeat 12 times, then 10 minutes easy. Heart rate will rise toward {hard_hr} by the last reps.",
                  "Ulangi 12 kali, lalu 10 menit santai. Detak jantung naik ke arah {hard_hr} di repetisi terakhir.")]},
        {"id": "pyramid", "acts": "run", "zone": Z_HARD,
         "label": ("Pyramid intervals 1-2-3-2-1", "Interval piramida 1-2-3-2-1"),
         "what": ("Intervals that get longer, then shorter again, like climbing up and down a pyramid. You run hard "
                  "for 1 minute, then 2, then 3, then back down to 2 and 1, with an easy jog after each that "
                  "lasts as long as the hard part before it.",
                  "Interval yang makin panjang lalu memendek lagi, seperti naik lalu turun piramida. Kamu lari cepat "
                  "1 menit, lalu 2, lalu 3, lalu turun lagi ke 2 dan 1, dengan jogging santai setelah tiap bagian "
                  "yang lamanya sama dengan bagian cepat sebelumnya."),
         "how": [("Warm up: 10 minutes easy jog.", "Pemanasan: 10 menit jogging santai."),
                 ("Fast 1 min → easy jog 1 min.", "Cepat 1 menit → jogging santai 1 menit."),
                 ("Fast 2 min → easy jog 2 min.", "Cepat 2 menit → jogging santai 2 menit."),
                 ("Fast 3 min → easy jog 3 min.", "Cepat 3 menit → jogging santai 3 menit."),
                 ("Fast 2 min → easy jog 2 min, then fast 1 min.", "Cepat 2 menit → jogging santai 2 menit, lalu cepat 1 menit."),
                 ("'Fast' = hard but controlled, heart rate {hard_hr}; run the short ones a little quicker than "
                  "the long one. Cool down 10 minutes easy.",
                  "'Cepat' = berat tapi terkendali, detak jantung {hard_hr}; bagian pendek sedikit lebih cepat dari "
                  "bagian panjang. Pendinginan 10 menit santai.")]},
        {"id": "fartlek", "acts": "run", "zone": (0.75, 0.90),
         "label": ("Fartlek (speed play)", "Fartlek (permainan kecepatan)"),
         "what": ("Swedish for 'speed play': an easy run with fast bursts whenever you feel like it, e.g. to the "
                  "next lamp post or tree. Less structured, more fun, and it builds the ability to change pace.",
                  "Bahasa Swedia untuk 'permainan kecepatan': lari santai dengan akselerasi kapan pun kamu mau, mis. "
                  "sampai tiang lampu atau pohon berikutnya. Lebih bebas, lebih seru, dan melatih kemampuan "
                  "mengubah pace."),
         "how": [("Run easy for 10 minutes to warm up.", "Lari santai 10 menit untuk pemanasan."),
                 ("Then add 8 surges of 1–2 minutes at a hard effort (heart rate up to {hard_hr}).",
                  "Lalu tambahkan 8 akselerasi 1–2 menit di usaha berat (detak jantung sampai {hard_hr})."),
                 ("Between surges, jog easily until you feel ready again (at least 2 minutes).",
                  "Di antara akselerasi, jogging santai sampai merasa siap lagi (minimal 2 menit)."),
                 ("Finish with 10 minutes easy.", "Akhiri dengan 10 menit santai.")]},
        {"id": "sprints", "acts": "run", "zone": None,
         "label": ("Sprint intervals", "Sprint interval"),
         "what": ("Very short, near-maximal sprints with full recovery. They build power and running economy. "
                  "Heart rate lags behind on efforts this short, so go by feel.",
                  "Sprint sangat pendek hampir maksimal dengan pemulihan penuh. Membangun tenaga dan efisiensi lari. "
                  "Detak jantung tertinggal pada usaha sesingkat ini, jadi pakai patokan rasa."),
         "how": [("Warm up: 15 minutes easy jog plus a few strides.", "Pemanasan: 15 menit jogging santai plus beberapa strides."),
                 ("Sprint 20 seconds at about 95% effort, upright and relaxed.",
                  "Sprint 20 detik di sekitar 95% usaha, badan tegak dan rileks."),
                 ("Walk or jog slowly for 2–3 minutes until fully recovered.",
                  "Jalan atau jogging pelan 2–3 menit sampai benar-benar pulih."),
                 ("Repeat 8 times, then cool down 10 minutes easy.", "Ulangi 8 kali, lalu pendinginan 10 menit santai.")]},
    ],
}

# Bodyweight strength (no equipment). Each routine lists exercises with how-to.
EXERCISES = {
    "glute_bridge": (("Glute bridge", "Glute bridge"), ("12–15", "12–15"), (
        "Lie on your back, knees bent, feet flat. Squeeze your bottom and lift your hips until shoulders, hips and "
        "knees form a straight line. Hold 1 second, lower slowly. Strengthens glutes and hamstrings, which keep "
        "your hips stable and take load off the knees.",
        "Berbaring telentang, lutut ditekuk, telapak kaki di lantai. Kencangkan bokong dan angkat pinggul sampai "
        "bahu, pinggul dan lutut lurus. Tahan 1 detik, turunkan perlahan. Menguatkan bokong dan paha belakang yang "
        "menjaga pinggul stabil dan mengurangi beban lutut.")),
    "chair_squat": (("Chair squat", "Chair squat"), ("10–12", "10–12"), (
        "Stand in front of a chair, feet hip-width. Sit back slowly for 3 seconds until you just touch the seat, "
        "then stand up by pushing through your heels. Knees follow your toes. Builds the thigh and hip strength "
        "you use on every stride.",
        "Berdiri di depan kursi, kaki selebar pinggul. Duduk ke belakang perlahan selama 3 detik sampai pantat "
        "menyentuh kursi, lalu berdiri dengan mendorong lewat tumit. Lutut searah ujung kaki. Membangun kekuatan "
        "paha dan pinggul yang dipakai tiap langkah.")),
    "calf_raise": (("Calf raise", "Calf raise"), ("15–20", "15–20"), (
        "Stand tall (hold a wall for balance). Rise onto your toes, hold 1 second at the top, lower slowly. "
        "Strengthens calves and the Achilles tendon, which absorb a lot of force when running.",
        "Berdiri tegak (pegang dinding untuk keseimbangan). Jinjit, tahan 1 detik di atas, turunkan perlahan. "
        "Menguatkan betis dan tendon Achilles yang menyerap banyak gaya saat lari.")),
    "reverse_lunge": (("Reverse lunge", "Reverse lunge"), ("6–8 per leg", "6–8 per kaki"), (
        "Step one foot back and lower until both knees are bent about 90°, front knee above the ankle. Push "
        "through the front heel to stand. Kinder on the knees than a forward lunge; builds single-leg strength.",
        "Langkahkan satu kaki ke belakang dan turunkan badan sampai kedua lutut menekuk sekitar 90°, lutut depan "
        "di atas pergelangan kaki. Dorong lewat tumit depan untuk berdiri. Lebih ramah lutut dibanding lunge ke "
        "depan; membangun kekuatan satu kaki.")),
    "plank": (("Forearm plank", "Forearm plank"), ("20–40 s", "20–40 detik"), (
        "Rest on forearms and toes, body in a straight line from head to heels. Tighten your belly, don't let "
        "the hips sag. Keeps your posture upright when you're tired late in a run.",
        "Bertumpu pada lengan bawah dan ujung kaki, badan lurus dari kepala ke tumit. Kencangkan perut, jangan "
        "biarkan pinggul turun. Menjaga postur tetap tegak saat lelah di akhir lari.")),
    "side_plank": (("Side plank", "Side plank"), ("20–30 s per side", "20–30 detik per detikisi"), (
        "Lie on your side, prop up on one forearm, lift your hips so the body is straight. Works the side of the "
        "core and hips that stop you from wobbling side to side.",
        "Berbaring miring, bertumpu pada satu lengan bawah, angkat pinggul sampai badan lurus. Melatih sisi otot "
        "inti dan pinggul yang mencegah badan goyang ke samping.")),
    "single_leg_bridge": (("Single-leg glute bridge", "Glute bridge satu kaki"), ("8–10 per leg", "8–10 per kaki"), (
        "Like a glute bridge but with one leg straight in the air. Keep the hips level as you lift. "
        "Running is a series of one-leg hops, so this matches it closely.",
        "Seperti glute bridge tapi satu kaki lurus di udara. Jaga pinggul tetap rata saat mengangkat. "
        "Lari adalah rangkaian lompatan satu kaki, jadi gerakan ini sangat mirip.")),
    "step_up": (("Step-up", "Step-up"), ("8–10 per leg", "8–10 per kaki"), (
        "Step onto a sturdy stair or low bench with one foot and drive up until standing tall on it, then step "
        "down slowly. Use the top leg, not a push from the bottom foot.",
        "Naik ke anak tangga atau bangku rendah yang kokoh dengan satu kaki dan dorong sampai berdiri tegak, lalu "
        "turun perlahan. Pakai tenaga kaki atas, bukan dorongan kaki bawah.")),
    "single_leg_calf_raise": (("Single-leg calf raise", "Calf raise satu kaki"), ("10–12 per leg", "10–12 per kaki"), (
        "A calf raise on one foot, holding a wall for balance. Harder than two feet; great for Achilles strength.",
        "Calf raise dengan satu kaki sambil berpegangan dinding. Lebih berat dari dua kaki; bagus untuk kekuatan "
        "Achilles.")),
    "bird_dog": (("Bird dog", "Bird dog"), ("8 per side", "8 per detikisi"), (
        "On hands and knees, reach one arm forward and the opposite leg back until both are straight, hold "
        "2 seconds, return. Keep your back flat. Trains core control and balance.",
        "Posisi merangkak, julurkan satu tangan ke depan dan kaki seberangnya ke belakang sampai lurus, tahan "
        "2 detik, kembali. Punggung tetap rata. Melatih kontrol inti dan keseimbangan.")),
    "dead_bug": (("Dead bug", "Dead bug"), ("8 per side", "8 per detikisi"), (
        "Lie on your back, arms up, knees bent at 90° above the hips. Slowly lower one arm and the opposite leg "
        "toward the floor while pressing your lower back down, then switch. Strong core without straining the back.",
        "Berbaring telentang, tangan ke atas, lutut menekuk 90° di atas pinggul. Turunkan perlahan satu tangan dan "
        "kaki seberangnya ke arah lantai sambil menekan punggung bawah ke lantai, lalu ganti. Menguatkan inti tanpa "
        "membebani punggung.")),
    "clamshell": (("Clamshell", "Clamshell"), ("12–15 per side", "12–15 per detikisi"), (
        "Lie on your side, knees bent, feet together. Keeping feet touching, open the top knee like a clamshell, "
        "then close slowly. Strengthens the outer hip that keeps knees from caving in.",
        "Berbaring miring, lutut ditekuk, kaki rapat. Dengan kaki tetap menempel, buka lutut atas seperti kerang, "
        "lalu tutup perlahan. Menguatkan pinggul luar yang menjaga lutut tidak jatuh ke dalam.")),
    "wall_sit": (("Wall sit", "Wall sit"), ("30–45 s", "30–45 detik"), (
        "Lean your back against a wall and slide down until knees are bent about 90°, as if sitting on an "
        "invisible chair. Hold. Builds thigh endurance for long runs and downhills.",
        "Sandarkan punggung ke dinding dan turun sampai lutut menekuk sekitar 90°, seperti duduk di kursi tak "
        "terlihat. Tahan. Membangun daya tahan paha untuk lari jauh dan turunan.")),
}

STRENGTH = [
    {"id": "classic", "label": ("Legs & core", "Kaki & inti"),
     "what": ("A full lower-body and core routine: the basics every runner needs for stable hips, strong knees "
              "and an upright posture.",
              "Rutinitas lengkap tubuh bawah dan inti: dasar yang dibutuhkan setiap pelari untuk pinggul stabil, "
              "lutut kuat dan postur tegak."),
     "moves": ["glute_bridge", "chair_squat", "calf_raise", "reverse_lunge", "plank"]},
    {"id": "single_leg", "label": ("Single-leg stability", "Stabilitas satu kaki"),
     "what": ("Running happens on one leg at a time, so this routine trains each leg alone, plus balance.",
              "Lari terjadi pada satu kaki bergantian, jadi rutinitas ini melatih tiap kaki sendiri-sendiri, "
              "plus keseimbangan."),
     "moves": ["single_leg_bridge", "step_up", "single_leg_calf_raise", "side_plank", "bird_dog"]},
    {"id": "core_hips", "label": ("Core & hips", "Inti & pinggul"),
     "what": ("Focus on the deep core and outer hips that keep your pelvis and knees lined up when you're tired.",
              "Fokus pada otot inti dalam dan pinggul luar yang menjaga panggul dan lutut tetap sejajar saat lelah."),
     "moves": ["dead_bug", "clamshell", "side_plank", "plank", "glute_bridge", "wall_sit"]},
]
REST_BETWEEN = ("Rest 45–60 seconds between exercises. Do all exercises once = 1 round.",
                "Istirahat 45–60 detik antar gerakan. Semua gerakan sekali = 1 putaran.")


def zone_text(z: tuple | None, max_hr: float | None, lang: str) -> str:
    if not z:
        return ""
    if max_hr:
        return f"{round(z[0] * max_hr)}–{round(z[1] * max_hr)} bpm"
    return f"{z[0]:.0%}–{z[1]:.0%} " + ("HR maks" if lang == "id" else "of max HR")


def fill(text: str, max_hr: float | None, paces: dict, lang: str) -> str:
    from .plan import fmt_pace

    def pace(k):
        return fmt_pace(paces[k]) if paces.get(k) else ("pace " + k)
    vals = {"easy_hr": zone_text(Z_EASY, max_hr, lang), "long_hr": zone_text(Z_LONG, max_hr, lang),
            "tempo_hr": zone_text(Z_TEMPO, max_hr, lang), "hard_hr": zone_text(Z_HARD, max_hr, lang),
            "walk_hr": zone_text(Z_WALK, max_hr, lang),
            "recovery_top": f"{round(0.72 * max_hr)} bpm" if max_hr else ("72% HR maks" if lang == "id" else "72% of max HR"),
            "easy_pace": pace("easy"), "tempo_pace": pace("tempo"), "int_pace": pace("interval"),
            "race_pace": pace("race")}
    return text.format(**vals)
