from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, flash
)
from functools import wraps
import json
import os
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'investasi_expert_system_2024'

# ─────────────────────────────────────────────
#  KONFIGURASI ADMIN
#  Password di-hash dengan SHA-256 + salt agar
#  tidak tersimpan plaintext di source code.
#
#  Untuk mengubah password, jalankan di terminal:
#    python -c "import hashlib; print(hashlib.sha256(b'salt_investiq_2024' + b'PASSWORD_BARU').hexdigest())"
#  Salin hasilnya ke ADMIN_PASSWORD_HASH di bawah.
# ─────────────────────────────────────────────
ADMIN_USERNAME      = 'admin'
ADMIN_PASSWORD_HASH = hashlib.sha256(
    b'salt_investiq_2024' + b'admin123'
).hexdigest()
# Hash di atas setara password: admin123
# Ganti b'admin123' dengan password baru Anda

def hash_password(password: str) -> str:
    """Hash password dengan SHA-256 + salt."""
    return hashlib.sha256(
        b'salt_investiq_2024' + password.encode()
    ).hexdigest()

# ─────────────────────────────────────────────
#  DECORATOR: login_required
#  Melindungi route pakar dari akses langsung
#  tanpa autentikasi session server-side.
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('pakar_logged_in'):
            # Simpan URL tujuan agar bisa redirect setelah login
            session['next_url'] = request.url
            flash('Silakan login sebagai admin terlebih dahulu.', 'warning')
            return redirect(url_for('pakar_login'))
        return f(*args, **kwargs)
    return decorated_function

# ─────────────────────────────────────────────
#  BASE KNOWLEDGE: PERTANYAAN (FAKTA)
# ─────────────────────────────────────────────
QUESTIONS = [
    {"id": "Q1",  "text": "Apakah usia Anda saat ini di bawah 35 tahun?",                                                                                 "category": "Demografis"},
    {"id": "Q2",  "text": "Apakah Anda saat ini memiliki tanggungan keluarga (pasangan, anak, atau orang tua)?",                                           "category": "Demografis"},
    {"id": "Q3",  "text": "Apakah penghasilan bulanan Anda di atas Rp 10.000.000?",                                                                        "category": "Finansial"},
    {"id": "Q4",  "text": "Apakah Anda sudah memiliki dana darurat minimal 6 bulan pengeluaran?",                                                          "category": "Finansial"},
    {"id": "Q5",  "text": "Apakah Anda saat ini memiliki hutang atau cicilan jangka panjang yang signifikan (KPR, KKB, dll)?",                             "category": "Finansial"},
    {"id": "Q6",  "text": "Apakah Anda memiliki asuransi jiwa atau asuransi kesehatan yang aktif saat ini?",                                               "category": "Finansial"},
    {"id": "Q7",  "text": "Apakah Anda sudah memiliki pengalaman berinvestasi lebih dari 3 tahun?",                                                        "category": "Pengalaman"},
    {"id": "Q8",  "text": "Apakah Anda memahami konsep diversifikasi portofolio dan manfaatnya dalam mengurangi risiko?",                                   "category": "Pengalaman"},
    {"id": "Q9",  "text": "Apakah Anda pernah berinvestasi pada instrumen berisiko tinggi seperti saham atau reksa dana saham?",                           "category": "Pengalaman"},
    {"id": "Q10", "text": "Apakah Anda bersedia menerima penurunan nilai investasi lebih dari 20% dalam jangka pendek demi potensi keuntungan lebih besar?","category": "Toleransi Risiko"},
    {"id": "Q11", "text": "Apakah Anda lebih memilih keamanan modal (tidak rugi) daripada kemungkinan memperoleh keuntungan besar?",                       "category": "Toleransi Risiko"},
    {"id": "Q12", "text": "Apakah Anda merasa nyaman jika nilai portofolio investasi Anda berfluktuasi secara signifikan setiap harinya?",                 "category": "Toleransi Risiko"},
    {"id": "Q13", "text": "Apakah tujuan utama investasi Anda adalah untuk jangka panjang (lebih dari 5 tahun), seperti pensiun atau pendidikan anak?",    "category": "Tujuan"},
    {"id": "Q14", "text": "Apakah Anda menginvestasikan dana yang tidak akan Anda butuhkan dalam waktu dekat (bukan dana kebutuhan rutin)?",               "category": "Tujuan"},
    {"id": "Q15", "text": "Apakah Anda cenderung membuat keputusan investasi berdasarkan analisis dan data, bukan berdasarkan rumor atau tren sesaat?",    "category": "Perilaku"},
    {"id": "Q16", "text": "Apakah Anda tetap mempertahankan (tidak menjual panik) investasi Anda ketika pasar sedang turun tajam?",                        "category": "Perilaku"},
]

# ─────────────────────────────────────────────
#  DEFAULT RULES + CF VALUES
# ─────────────────────────────────────────────
DEFAULT_RULES = {
    "sangat_konservatif": {
        "label": "Sangat Konservatif",
        "color": "#4ade80",
        "description": "Profil ini sangat mengutamakan keamanan modal. Investor cocok dengan instrumen seperti deposito, tabungan, dan obligasi pemerintah dengan risiko sangat rendah.",
        "rekomendasi": ["Deposito Bank", "Tabungan Berjangka", "Obligasi Negara Ritel (ORI)", "Reksa Dana Pasar Uang"],
        "rules": [
            {"conditions": [{"qid": "Q11", "value": True},  {"qid": "Q10", "value": False}, {"qid": "Q12", "value": False}], "cf": 0.93},
            {"conditions": [{"qid": "Q4",  "value": False}, {"qid": "Q5",  "value": True},  {"qid": "Q11", "value": True},  {"qid": "Q10", "value": False}], "cf": 0.90},
            {"conditions": [{"qid": "Q7",  "value": False}, {"qid": "Q8",  "value": False}, {"qid": "Q9",  "value": False}, {"qid": "Q10", "value": False}], "cf": 0.85},
            {"conditions": [{"qid": "Q13", "value": False}, {"qid": "Q14", "value": False}, {"qid": "Q11", "value": True},  {"qid": "Q12", "value": False}], "cf": 0.86},
            {"conditions": [{"qid": "Q2",  "value": True},  {"qid": "Q4",  "value": False}, {"qid": "Q16", "value": False}, {"qid": "Q10", "value": False}], "cf": 0.82},
            {"conditions": [{"qid": "Q15", "value": False}, {"qid": "Q16", "value": False}, {"qid": "Q10", "value": False}, {"qid": "Q11", "value": True}],  "cf": 0.80},
        ]
    },
    "konservatif": {
        "label": "Konservatif",
        "color": "#60a5fa",
        "description": "Investor dengan profil ini lebih menyukai investasi aman dengan sedikit toleransi terhadap risiko. Cocok untuk instrumen pendapatan tetap.",
        "rekomendasi": ["Reksa Dana Pendapatan Tetap", "Obligasi Korporasi", "ORI/SBR", "Deposito"],
        "rules": [
            {"conditions": [{"qid": "Q11", "value": True},  {"qid": "Q10", "value": False}, {"qid": "Q4",  "value": True},  {"qid": "Q5",  "value": False}], "cf": 0.85},
            {"conditions": [{"qid": "Q7",  "value": False}, {"qid": "Q8",  "value": True},  {"qid": "Q9",  "value": False}, {"qid": "Q10", "value": False}], "cf": 0.80},
            {"conditions": [{"qid": "Q13", "value": False}, {"qid": "Q14", "value": True},  {"qid": "Q12", "value": False}, {"qid": "Q10", "value": False}], "cf": 0.78},
            {"conditions": [{"qid": "Q2",  "value": True},  {"qid": "Q6",  "value": True},  {"qid": "Q11", "value": True},  {"qid": "Q4",  "value": True}],  "cf": 0.77},
            {"conditions": [{"qid": "Q9",  "value": False}, {"qid": "Q15", "value": True},  {"qid": "Q16", "value": True},  {"qid": "Q10", "value": False}], "cf": 0.82},
            {"conditions": [{"qid": "Q3",  "value": False}, {"qid": "Q4",  "value": True},  {"qid": "Q10", "value": False}, {"qid": "Q11", "value": True}],  "cf": 0.76},
        ]
    },
    "moderat": {
        "label": "Moderat",
        "color": "#f59e0b",
        "description": "Investor moderat menerima risiko menengah demi potensi keuntungan yang lebih baik. Portofolio campuran antara saham dan obligasi sangat disarankan.",
        "rekomendasi": ["Reksa Dana Campuran", "Saham Blue Chip", "Obligasi Korporasi", "ETF"],
        "rules": [
            {"conditions": [{"qid": "Q8",  "value": True},  {"qid": "Q11", "value": False}, {"qid": "Q10", "value": False}, {"qid": "Q12", "value": False}], "cf": 0.85},
            {"conditions": [{"qid": "Q4",  "value": True},  {"qid": "Q7",  "value": True},  {"qid": "Q12", "value": False}, {"qid": "Q10", "value": False}], "cf": 0.82},
            {"conditions": [{"qid": "Q13", "value": True},  {"qid": "Q14", "value": True},  {"qid": "Q9",  "value": False}, {"qid": "Q10", "value": False}], "cf": 0.80},
            {"conditions": [{"qid": "Q1",  "value": True},  {"qid": "Q15", "value": True},  {"qid": "Q10", "value": False}, {"qid": "Q11", "value": False}], "cf": 0.78},
            {"conditions": [{"qid": "Q3",  "value": True},  {"qid": "Q2",  "value": True},  {"qid": "Q16", "value": True},  {"qid": "Q10", "value": False}], "cf": 0.75},
            {"conditions": [{"qid": "Q9",  "value": True},  {"qid": "Q11", "value": False}, {"qid": "Q16", "value": True},  {"qid": "Q10", "value": False}], "cf": 0.83},
        ]
    },
    "agresif": {
        "label": "Agresif",
        "color": "#f87171",
        "description": "Investor agresif siap menghadapi risiko tinggi demi potensi keuntungan maksimal. Cocok untuk saham pertumbuhan, kripto, atau instrumen derivatif.",
        "rekomendasi": ["Saham Growth", "Reksa Dana Saham", "Kripto (sebagian kecil)", "ETF Tematik"],
        "rules": [
            {"conditions": [{"qid": "Q10", "value": True},  {"qid": "Q11", "value": False}, {"qid": "Q12", "value": True}],                                  "cf": 0.95},
            {"conditions": [{"qid": "Q4",  "value": True},  {"qid": "Q9",  "value": True},  {"qid": "Q16", "value": True},  {"qid": "Q12", "value": True}],  "cf": 0.90},
            {"conditions": [{"qid": "Q1",  "value": True},  {"qid": "Q13", "value": True},  {"qid": "Q14", "value": True},  {"qid": "Q10", "value": True}],  "cf": 0.88},
            {"conditions": [{"qid": "Q7",  "value": True},  {"qid": "Q8",  "value": True},  {"qid": "Q15", "value": True},  {"qid": "Q10", "value": True}],  "cf": 0.85},
            {"conditions": [{"qid": "Q3",  "value": True},  {"qid": "Q5",  "value": False}, {"qid": "Q6",  "value": True},  {"qid": "Q10", "value": True}],  "cf": 0.82},
            {"conditions": [{"qid": "Q12", "value": True},  {"qid": "Q15", "value": True},  {"qid": "Q10", "value": True},  {"qid": "Q11", "value": False}], "cf": 0.92},
        ]
    }
}

CF_THRESHOLD = 0.60

# ─────────────────────────────────────────────
#  LOAD / SAVE RULES
# ─────────────────────────────────────────────
RULES_FILE = 'rules_data.json'

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_RULES

def save_rules(rules):
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)

# ─────────────────────────────────────────────
#  FORWARD CHAINING + CERTAINTY FACTOR ENGINE
# ─────────────────────────────────────────────
def combine_cf(cf1, cf2):
    """Kombinasi CF paralel: CF1 + CF2 * (1 - CF1)"""
    if cf1 >= 0 and cf2 >= 0:
        return cf1 + cf2 * (1 - cf1)
    elif cf1 < 0 and cf2 < 0:
        return cf1 + cf2 * (1 + cf1)
    else:
        return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))

def evaluate_rule(conditions, facts):
    """Evaluasi satu rule. Return True jika semua kondisi terpenuhi."""
    for cond in conditions:
        if cond["qid"] not in facts:
            return False
        if facts[cond["qid"]] != cond["value"]:
            return False
    return True

def forward_chaining_cf(facts, rules):
    """Forward Chaining + CF. Return results (≥ threshold), trace, raw (semua)."""
    results, trace, raw = {}, {}, {}

    for profile_key, profile_data in rules.items():
        combined_cf = None
        fired_rules = []

        for idx, rule in enumerate(profile_data["rules"]):
            if evaluate_rule(rule["conditions"], facts):
                fired_rules.append({
                    "rule_idx"  : idx + 1,
                    "conditions": rule["conditions"],
                    "cf"        : rule["cf"]
                })
                combined_cf = (
                    rule["cf"] if combined_cf is None
                    else combine_cf(combined_cf, rule["cf"])
                )

        combined_cf        = combined_cf if combined_cf is not None else 0.0
        pct                = round(combined_cf * 100, 2)
        raw[profile_key]   = pct
        trace[profile_key] = fired_rules

        if combined_cf >= CF_THRESHOLD:
            results[profile_key] = pct

    return results, trace, raw

# ═════════════════════════════════════════════
#  ROUTES — PUBLIK
# ═════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    session.clear()
    session['answers']   = {}
    session['current_q'] = 0
    session['name']      = request.form.get('name', 'Investor')
    return redirect(url_for('question'))

@app.route('/question')
def question():
    idx = session.get('current_q', 0)
    if idx >= len(QUESTIONS):
        return redirect(url_for('result'))
    q        = QUESTIONS[idx]
    total    = len(QUESTIONS)
    progress = round((idx / total) * 100)
    return render_template('question.html',
                           question=q, index=idx,
                           total=total, progress=progress,
                           name=session.get('name', 'Investor'))

@app.route('/answer', methods=['POST'])
def answer():
    idx = session.get('current_q', 0)
    if idx >= len(QUESTIONS):
        return redirect(url_for('result'))
    ans                  = request.form.get('answer')
    qid                  = QUESTIONS[idx]['id']
    answers              = session.get('answers', {})
    answers[qid]         = (ans == 'ya')
    session['answers']   = answers
    session['current_q'] = idx + 1
    return redirect(url_for('question'))

@app.route('/result')
def result():
    facts = session.get('answers', {})
    if not facts:
        return redirect(url_for('index'))

    rules                    = load_rules()
    cf_results, trace, raw   = forward_chaining_cf(facts, rules)

    # Tentukan profil terbaik
    if cf_results:
        best_profile = max(cf_results, key=cf_results.get)
        best_cf      = cf_results[best_profile]
    else:
        best_profile = max(raw, key=raw.get)
        best_cf      = raw[best_profile]
        if best_cf == 0:
            score = sum([
                 1 if facts.get("Q6")  else -1,
                 1 if facts.get("Q10") else -1,
                 1 if facts.get("Q1")  else  0,
                 1 if facts.get("Q5")  else  0,
                -1 if facts.get("Q9")  else  1,
                -1 if facts.get("Q3")  else  0,
            ])
            best_profile = (
                "sangat_konservatif" if score <= -2 else
                "konservatif"        if score <=  0 else
                "moderat"            if score <=  2 else
                "agresif"
            )
            raw[best_profile] = 60.0
            best_cf = 60.0

    profile_info       = rules.get(best_profile, DEFAULT_RULES[best_profile])
    secondary_profiles = {
        k: v for k, v in cf_results.items()
        if k != best_profile and (best_cf - v) <= 20.0
    }

    answered = [
        {"id": q['id'], "text": q['text'],
         "category": q['category'], "answer": facts[q['id']]}
        for q in QUESTIONS if q['id'] in facts
    ]
    timestamp = datetime.now().strftime("%d %B %Y, %H:%M")

    return render_template(
        'result.html',
        name               = session.get('name', 'Investor'),
        profile_key        = best_profile,
        profile            = profile_info,
        cf_results         = cf_results,
        raw_results        = raw,
        secondary_profiles = secondary_profiles,
        cf_threshold       = CF_THRESHOLD * 100,
        trace              = trace.get(best_profile, []),
        answered           = answered,
        timestamp          = timestamp,
        all_profiles       = rules
    )

# ═════════════════════════════════════════════
#  ROUTES — AUTENTIKASI PAKAR
# ═════════════════════════════════════════════

@app.route('/pakar/login', methods=['GET', 'POST'])
def pakar_login():
    """
    GET  → tampilkan halaman login
    POST → verifikasi username + password
    """
    # Jika sudah login, langsung ke panel
    if session.get('pakar_logged_in'):
        return redirect(url_for('pakar'))

    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if (username == ADMIN_USERNAME and
                hash_password(password) == ADMIN_PASSWORD_HASH):
            # ✅ Login berhasil — set server-side session
            session['pakar_logged_in'] = True
            session['pakar_username']  = username
            session.permanent          = False  # session habis saat browser tutup

            # Redirect ke URL tujuan semula (jika ada), atau ke panel
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('pakar'))
        else:
            # ❌ Kredensial salah
            error = 'Username atau password salah. Silakan coba lagi.'

    return render_template('pakar_login.html', error=error)


@app.route('/pakar/logout', methods=['POST'])
def pakar_logout():
    """Hapus session pakar dan redirect ke home."""
    session.pop('pakar_logged_in', None)
    session.pop('pakar_username',  None)
    flash('Anda telah berhasil keluar dari Panel Pakar.', 'info')
    return redirect(url_for('index'))


# ═════════════════════════════════════════════
#  ROUTES — PANEL PAKAR (dilindungi login_required)
# ═════════════════════════════════════════════

@app.route('/pakar')
@login_required
def pakar():
    rules = load_rules()
    return render_template(
        'pakar.html',
        rules        = rules,
        questions    = QUESTIONS,
        cf_threshold = CF_THRESHOLD,
        admin_user   = session.get('pakar_username', 'admin')
    )


@app.route('/pakar/update_cf', methods=['POST'])
@login_required
def update_cf():
    data     = request.get_json()
    rules    = load_rules()
    profile  = data.get('profile')
    rule_idx = int(data.get('rule_idx'))
    new_cf   = float(data.get('cf'))

    if not (0.0 <= new_cf <= 1.0):
        return jsonify({'status': 'error', 'message': 'CF harus antara 0 dan 1'}), 400

    if profile in rules and rule_idx < len(rules[profile]['rules']):
        rules[profile]['rules'][rule_idx]['cf'] = round(new_cf, 2)
        save_rules(rules)
        return jsonify({'status': 'ok', 'message': 'CF berhasil diperbarui'})

    return jsonify({'status': 'error', 'message': 'Rule tidak ditemukan'}), 404


@app.route('/pakar/add_rule', methods=['POST'])
@login_required
def add_rule():
    data       = request.get_json()
    rules      = load_rules()
    profile    = data.get('profile')
    conditions = data.get('conditions', [])
    cf         = float(data.get('cf', 0.5))

    if profile not in rules:
        return jsonify({'status': 'error', 'message': 'Profil tidak ditemukan'}), 404

    new_rule = {
        "conditions": [{"qid": c["qid"], "value": c["value"]} for c in conditions],
        "cf": round(cf, 2)
    }
    rules[profile]['rules'].append(new_rule)
    save_rules(rules)

    return jsonify({
        'status'  : 'ok',
        'message' : 'Rule berhasil ditambahkan',
        'rule_idx': len(rules[profile]['rules']) - 1
    })


@app.route('/pakar/delete_rule', methods=['POST'])
@login_required
def delete_rule():
    data     = request.get_json()
    rules    = load_rules()
    profile  = data.get('profile')
    rule_idx = int(data.get('rule_idx'))

    if profile in rules and 0 <= rule_idx < len(rules[profile]['rules']):
        rules[profile]['rules'].pop(rule_idx)
        save_rules(rules)
        return jsonify({'status': 'ok', 'message': 'Rule dihapus'})

    return jsonify({'status': 'error', 'message': 'Rule tidak ditemukan'}), 404


@app.route('/pakar/reset', methods=['POST'])
@login_required
def reset_rules():
    save_rules(DEFAULT_RULES)
    return jsonify({'status': 'ok', 'message': 'Rules direset ke default'})


@app.route('/api/rules')
@login_required
def get_rules():
    return jsonify(load_rules())


# ═════════════════════════════════════════════
if __name__ == '__main__':
    if not os.path.exists(RULES_FILE):
        save_rules(DEFAULT_RULES)
    app.run(debug=True, port=5000)