"""Translations. English is the source text and the lookup key; ID holds Bahasa Indonesia.
A missing key falls back to English, so untranslated text never breaks a page."""
import re
from datetime import date

LANGS = {"en": "English", "id": "Bahasa Indonesia"}

ID = {
    # header / footer
    "My plan": "Program saya", "New plan": "Program baru", "Log out": "Keluar", "Admin": "Admin",
    "Language": "Bahasa", "Menu": "Menu", "Support": "Bantuan", "Privacy": "Privasi", "Source": "Kode sumber",
    # home
    "Your training plan, built from your own runs.": "Program latihanmu, dibuat dari larimu sendiri.",
    "Connect Strava, pick your race, and get a day-by-day plan that starts from where you are today.":
        "Hubungkan Strava, pilih lombamu, dan dapatkan program harian yang dimulai dari kondisimu saat ini.",
    "We only read your activities. You can delete your data at any time.":
        "Kami hanya membaca aktivitasmu. Datamu bisa dihapus kapan saja.",
    # new plan
    "Hi": "Hai", "what are you training for?": "lagi latihan untuk apa?",
    "Event date": "Tanggal lomba", "Distance": "Jarak", "Half marathon": "Half marathon", "Marathon": "Maraton",
    "Runs per week": "Lari per minggu", "Goal time in minutes": "Target waktu (menit)",
    "(optional, e.g. 55, or 119 for 1:59)": "(opsional, mis. 55, atau 119 untuk 1:59)",
    "Build my plan": "Buat programku",
    "Reads your last 12 weeks of Strava runs. Takes a few seconds.":
        "Membaca lari 12 minggu terakhir di Strava. Butuh beberapa detik.",
    "← Back to current plan": "← Kembali ke program saat ini",
    "Delete your Berlari data? This cannot be undone.": "Hapus data Berlari kamu? Ini tidak bisa dibatalkan.",
    "Delete my data": "Hapus dataku",
    # plan page
    "days to go": "hari lagi", "goal": "target", "From Strava": "Dari Strava", "km/week": "km/minggu",
    "longest": "terjauh", "typical pace": "pace rata-rata",
    "Fitness": "Kebugaran", "Fatigue": "Kelelahan", "Form": "Form",
    "fresh": "segar", "tired": "lelah", "balanced": "seimbang",
    "Change vs yesterday. Fitness = 6-week training load, fatigue = last week's, form = fitness − fatigue.":
        "Perubahan dari kemarin. Kebugaran = beban latihan 6 minggu, kelelahan = beban minggu lalu, "
        "form = kebugaran − kelelahan.",
    "Your current condition": "Kondisimu saat ini", "updated": "diperbarui",
    "Your coach is writing your summary. Refresh in a moment.":
        "Pelatihmu sedang menulis ringkasan. Muat ulang sebentar lagi.",
    "last 6 weeks": "6 minggu terakhir", "this week": "minggu ini", "per heartbeat": "per detak jantung",
    "Getting better": "Makin baik", "Keep an eye on": "Perlu diperhatikan", "Next few days": "Beberapa hari ke depan",
    "Recent runs": "Lari terbaru",
    "Coach notes for each day appear the evening before. The summary updates each evening after days you trained.":
        "Catatan pelatih untuk tiap hari muncul malam sebelumnya. Ringkasan diperbarui tiap malam "
        "setelah hari kamu berlatih.",
    "Custom plan": "Program kustom",
    "You're following a custom plan. Building a new plan here replaces it.":
        "Kamu sedang mengikuti program kustom. Membuat program baru di sini akan menggantinya.",
    "Run": "Lari", "Walk": "Jalan", "Strength": "Strength",
    "Variation": "Variasi", "Choose another variation": "Pilih variasi lain", "Save": "Simpan",
    "Routine": "Rutinitas", "Heart rate": "Detak jantung", "How to do it": "Cara melakukannya",
    "Checkpoint": "Checkpoint", "Phase": "Fase", "All phases": "Semua fase",
    "Sessions done so far in this phase": "Sesi selesai sejauh ini di fase ini",
    "Max heart rate": "HR maksimal",
    "highest seen in your runs; add your age in Settings to use the Tanaka formula.":
        "tertinggi yang terlihat di larimu; isi umurmu di Pengaturan untuk memakai rumus Tanaka.",
    "Add your age in Settings to see heart-rate ranges in bpm.":
        "Isi umurmu di Pengaturan untuk melihat rentang detak jantung dalam bpm.",
    "Settings": "Pengaturan", "Your age": "Umurmu", "(Strava doesn't share it)": "(Strava tidak membagikannya)",
    "Default variations": "Variasi bawaan",
    "Used for every upcoming session of that type, unless you pick something else on the day.":
        "Dipakai untuk setiap sesi mendatang jenis itu, kecuali kamu memilih yang lain di harinya.",
    "Recommended by the plan (changes by phase)": "Rekomendasi program (berubah per fase)",
    "Saved. Upcoming sessions now use your defaults.": "Tersimpan. Sesi mendatang kini memakai pilihan bawaanmu.",
    "Saved. Your plan is being rebuilt from today for your new height/weight; past days stay as they were.":
        "Tersimpan. Programmu sedang disusun ulang mulai hari ini sesuai tinggi/berat barumu; hari-hari yang lalu tetap seperti semula.",
    "Easy runs": "Lari santai", "Long runs": "Lari jauh", "Tempo runs": "Lari tempo",
    "Strength (bodyweight)": "Strength (tanpa alat)",
    "Today and tomorrow": "Hari ini dan besok", "Nothing planned.": "Tidak ada jadwal.",
    "Full schedule": "Jadwal lengkap", "Previous": "Sebelumnya", "Next": "Berikutnya", "Week": "Minggu ke",
    "Weeks": "Minggu",
    "About you": "Tentang kamu", "(helps make the plan safe for you)": "(membantu membuat program aman untukmu)",
    "Age": "Umur", "Height (cm)": "Tinggi (cm)", "Weight (kg)": "Berat (kg)",
    "Age sets your max heart rate (Tanaka formula; Strava doesn't share age). Height and weight let the plan build up more gently when needed. Only stored for your plan, never shared.":
        "Umur menentukan HR maksimalmu (rumus Tanaka; Strava tidak membagikan umur). Tinggi dan berat membuat "
        "program naik lebih perlahan bila perlu. Hanya disimpan untuk programmu, tidak pernah dibagikan.",
    "Plan adjusted for you": "Program disesuaikan untukmu",
    "Because running loads your joints with 2–3× your body weight on every stride, this plan builds up more slowly, peaks lower and keeps run-walk longer.":
        "Karena setiap langkah lari membebani sendi 2–3× berat badan, program ini naik lebih perlahan, puncaknya "
        "lebih rendah, dan memakai lari-jalan lebih lama.",
    "Please get a check-up from a doctor before the hard sessions (Norwegian 4x4, tempo), especially with high blood pressure, heart, diabetes or joint problems.":
        "Sebaiknya periksa ke dokter sebelum sesi berat (Norwegian 4x4, tempo), terutama bila punya tekanan darah "
        "tinggi, masalah jantung, diabetes atau sendi.",
    "Stop and rest": "Berhenti dan istirahat",
    "if you feel chest pain or pressure, dizziness, unusual shortness of breath, or sharp pain in a joint, shin or heel.":
        "bila merasa nyeri atau sesak di dada, pusing, napas pendek tidak biasa, atau nyeri tajam di sendi, tulang "
        "kering atau tumit.",
    "Sex": "Jenis kelamin", "(for calorie needs)": "(untuk kebutuhan kalori)", "Male": "Laki-laki", "Female": "Perempuan",
    "Meals": "Makanan", "protein": "protein", "carbs": "karbohidrat", "Target": "Target", "about": "sekitar",
    "week": "minggu", "weight loss": "turun berat", "During the long run": "Saat lari jauh",
    "Estimates for typical portions; check labels. General guidance, not a medical diet. With BMI 35+ or a health condition, check with a doctor or dietitian.":
        "Perkiraan untuk porsi umum; cek label. Panduan umum, bukan diet medis. Dengan BMI 35+ atau kondisi kesehatan "
        "tertentu, konsultasikan ke dokter atau ahli gizi.",
    "Fill in About you (age, sex, height, weight) to get daily meal suggestions.":
        "Isi Tentang kamu (umur, jenis kelamin, tinggi, berat) untuk mendapat saran makan harian.",
    "Your body uses about": "Tubuhmu memakai sekitar",
    "today (resting + daily life + training). Eat about": "hari ini (istirahat + aktivitas harian + latihan). Makan sekitar",
    "less, which is about": "lebih sedikit, sekitar",
    "When do you eat rice?": "Kapan kamu makan nasi?", "Every day": "Setiap hari",
    "Only on weekends (at home)": "Hanya akhir pekan (di rumah)", "Never": "Tidak pernah", "for the day": "untuk hari ini",
    "Prices are rough Jakarta-area estimates; stalls and promos vary. Home meals are priced as if bought at a stall.":
        "Harga adalah perkiraan kasar area Jakarta; tiap warung dan promo berbeda. Makanan rumah dihitung seperti beli di warung.",
    "Food budget per weekday (Rp)": "Budget makan per hari kerja (Rp)", "(optional)": "(opsional)",
    "Your budget covers about": "Budgetmu cukup untuk sekitar",
    "under today's target. Fine for weight loss on easy days; on hard days add a banana or a Fitbar if you feel drained.":
        "di bawah target hari ini. Tidak masalah untuk turun berat di hari ringan; di hari berat tambah pisang atau Fitbar bila terasa lemas.",
    "Week of": "Minggu", "Adjusted": "Disesuaikan", "Ran": "Lari", "in": "dalam", "min": "mnt",
    "Easy": "Santai", "Long": "Lari jauh", "Intervals": "Interval", "Tempo": "Tempo", "Rest": "Istirahat",
    "Race": "Lomba",
    "Done": "Selesai", "Partly done": "Sebagian", "Extra run": "Lari tambahan", "Missed": "Terlewat",
    # errors
    "Strava login was cancelled or failed. Try again.": "Login Strava dibatalkan atau gagal. Coba lagi.",
    "goal time must be in minutes, between 10 and 600 (e.g. 119 for 1:59)":
        "Target waktu harus dalam menit, antara 10 dan 600 (mis. 119 untuk 1:59).",
    "event must be in the future": "Tanggal lomba harus di masa depan.",
    "unknown distance": "Jarak tidak dikenal.",
    # admin
    "Strava athlete capacity": "Kapasitas atlet Strava", "of": "dari", "connected": "terhubung",
    "Full.": "Penuh.",
    "New athletes can't connect until Strava raises the limit (submit the review).":
        "Atlet baru tidak bisa terhubung sampai Strava menaikkan batas (ajukan review).",
    "Almost full: time to submit the Strava review.": "Hampir penuh: saatnya ajukan review Strava.",
    "Athletes": "Atlet", "(no name)": "(tanpa nama)", "on": "pada", "plan since": "program sejak",
    "no plan yet": "belum ada program", "runs": "lari", "last": "terakhir", "summary": "ringkasan",
    "Remove athlete": "Hapus atlet", "(you)": "(kamu)", "No athletes yet.": "Belum ada atlet.", "Remove": "Hapus",
    "This disconnects them from Strava and permanently deletes their plan and data.":
        "Ini memutus mereka dari Strava dan menghapus program serta datanya secara permanen.",
}

DAYS_ID = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
MONTHS_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
DAY_ABBR_ID = dict(zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], DAYS_ID))

# Workout details and adjustment labels are generated in English by plan.py and stored with the plan,
# so they're translated at display time. Keep in sync with plan.py (tests/test_i18n.py checks coverage).
PLAN_TEXT_ID = [
    (r"Rest or light mobility", "Istirahat atau mobilitas ringan"),
    (r"Easy at (\S+)", r"Lari santai di \1"),
    (r"Long run, conversational at (\S+)", r"Lari jauh, pace santai (masih bisa ngobrol) di \1"),
    (r"Warm up 2 km, 6×800 m at (\S+) with 400 m jog, cool down",
     r"Pemanasan 2 km, 6×800 m di \1 dengan jogging 400 m, lalu pendinginan"),
    (r"Warm up 2 km, (\d+) km at (\S+), cool down", r"Pemanasan 2 km, \1 km di \2, lalu pendinginan"),
    (r"Race day! Target (\S+)", r"Hari lomba! Target \1"),
    (r"Easy, conversational effort", "Santai, masih bisa sambil ngobrol"),
    (r"Long run moved here from (\w+) \(missed\)",
     lambda m: f"Lari jauh dipindah ke sini dari {DAY_ABBR_ID.get(m[1], m[1])} (terlewat)"),
    (r"Easy instead of hard: the day after a long run", "Santai, bukan latihan berat: sehari setelah lari jauh"),
    (r"Lighter: the previous phase goal wasn't reached", "Lebih ringan: target fase sebelumnya belum tercapai"),
    (r"Shorter: last week you ran (\d+) of (\d+) km", r"Dipersingkat: minggu lalu kamu lari \1 dari \2 km"),
    (r"Easy instead of (\w+): you're very tired \(form (-?\d+)\)",
     lambda m: f"Santai, bukan {'interval' if m[1] == 'intervals' else m[1]}: kamu sangat lelah (form {m[2]})"),
]


def t(text: str, lang: str) -> str:
    return ID.get(text, text) if lang == "id" else text


def plan_text(text: str, lang: str) -> str:
    if lang != "id" or not text:
        return text
    for pattern, repl in PLAN_TEXT_ID:
        out, n = re.subn(f"^{pattern}$", repl, text)
        if n:
            return out
    return text


def fmt_date(value, fmt: str, lang: str) -> str:
    """strftime with Indonesian day/month abbreviations when lang == 'id'."""
    d = date.fromisoformat(value) if isinstance(value, str) else value
    if lang == "id":
        fmt = fmt.replace("%a", DAYS_ID[d.weekday()]).replace("%b", MONTHS_ID[d.month - 1])
    return d.strftime(fmt)


def pick(accept_language: str) -> str:
    """First supported language in an Accept-Language header, else English."""
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return "en"
