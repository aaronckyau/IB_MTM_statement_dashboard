"""
IB Dashboard Flask App
Run: python app.py
Then open http://localhost:5000
"""
from flask import Flask, request, make_response
from parser import parse_mtm_csv, parse_mtm_csv_v2
from templates_builder import build_html

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB


LANDING_HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IB 結單儀表板</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'IBM Plex Sans',sans-serif;background:#f8faf8;color:#1c2b1e;min-height:100vh;display:flex;flex-direction:column}

/* Header — same as dashboard */
.site-header{background:#ffffff;border-bottom:2px solid #166534;padding:0 32px;display:flex;align-items:center;gap:14px}
.header-brand{display:flex;align-items:center;gap:14px;padding:16px 0}
.header-logo{width:36px;height:36px;background:#166534;border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.header-title{font-family:'Libre Baskerville',serif;font-size:16px;font-weight:700;color:#166534}
.header-sub{font-size:11px;color:#5a6e5c;margin-top:1px;font-family:'IBM Plex Mono',monospace}

/* Main area */
.main{flex:1;display:flex;align-items:center;justify-content:center;padding:48px 24px}
.card{background:#ffffff;border:1px solid #d4e4d4;border-radius:10px;width:100%;max-width:520px;overflow:hidden}
.card-header{padding:20px 28px;border-bottom:1px solid #e8f0e8;background:#f6fbf6}
.card-title{font-family:'Libre Baskerville',serif;font-size:18px;font-weight:700;color:#166534;margin-bottom:4px}
.card-sub{font-size:13px;color:#5a6e5c;line-height:1.6}
.card-body{padding:24px 28px}

/* Upload zone */
.upload-zone{border:1.5px dashed #bbddbf;border-radius:8px;padding:36px 24px;text-align:center;cursor:pointer;transition:border-color .2s,background .2s;display:block;background:#ffffff}
.upload-zone:hover,.upload-zone.drag{border-color:#166534;background:#f0f7f1}
input[type=file]{display:none}
.upload-icon{margin-bottom:14px}
.upload-title{font-size:15px;font-weight:600;color:#1c2b1e;margin-bottom:6px}
.upload-sub{font-size:12px;color:#8a9e8c;line-height:1.8}
.upload-sub b{color:#374840;font-weight:600}

/* Spinner */
.spinner{display:none;padding:28px;text-align:center}
.spinner-ring{width:32px;height:32px;border:3px solid #d4e4d4;border-top-color:#166534;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.spinner-text{font-size:13px;color:#8a9e8c;font-family:'IBM Plex Mono',monospace}

/* Feature grid */
.features{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px}
.feat{background:#f6fbf6;border:1px solid #e8f0e8;border-radius:7px;padding:12px 14px}
.feat-title{font-size:12px;font-weight:600;color:#374840;margin-bottom:2px}
.feat-desc{font-size:11px;color:#8a9e8c}
.feat-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#166534;margin-right:6px;vertical-align:middle}

/* Footer */
footer{text-align:center;padding:16px;font-size:11px;color:#8a9e8c;border-top:1px solid #e8f0e8;font-family:'IBM Plex Mono',monospace}
</style>
</head>
<body>

<header class="site-header">
  <div class="header-brand">
    <div class="header-logo">
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <path d="M3 14l4-5 3 3 3-4 4 6" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="16" cy="5" r="2" fill="white" opacity="0.7"/>
      </svg>
    </div>
    <div>
      <div class="header-title">IB 結單儀表板</div>
      <div class="header-sub">Interactive Brokers · 自動解析</div>
    </div>
  </div>
</header>

<div class="main">
  <div class="card">
    <div class="card-header">
      <div class="card-title">上載結單</div>
      <div class="card-sub">支援 IB MTM 總結及活動結單 CSV，中英文版本均可</div>
    </div>
    <div class="card-body">
      <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
        <label class="upload-zone" id="dropZone">
          <input type="file" name="file" id="csvInput" accept=".csv">
          <div class="upload-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#bbddbf" stroke-width="1.5" stroke-linecap="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
          </div>
          <div class="upload-title">拖放 CSV 或點擊上載</div>
          <div class="upload-sub">
            <b>MTM 總結</b>（以市值計 MTM 總結）&nbsp;·&nbsp;
            <b>活動結單</b>（Activity Statement）
          </div>
        </label>
      </form>

      <div class="spinner" id="spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-text">正在解析結單，請稍候…</div>
      </div>

      <div class="features">
        <div class="feat"><div class="feat-title"><span class="feat-dot"></span>淨資產值總覽</div><div class="feat-desc">期間變動及時間加權回報</div></div>
        <div class="feat"><div class="feat-title"><span class="feat-dot"></span>持倉明細</div><div class="feat-desc">股票、期權、外匯完整欄位</div></div>
        <div class="feat"><div class="feat-title"><span class="feat-dot"></span>收入費用分析</div><div class="feat-desc">股息、利息、行情費明細</div></div>
        <div class="feat"><div class="feat-title"><span class="feat-dot"></span>盈虧圖表</div><div class="feat-desc">各項盈虧來源視覺化</div></div>
      </div>
    </div>
  </div>
</div>

<footer>IB 結單儀表板 &nbsp;·&nbsp; 數據來自 Interactive Brokers &nbsp;·&nbsp; 僅供參考</footer>

<script>
const inp  = document.getElementById('csvInput');
const drop = document.getElementById('dropZone');
const form = document.getElementById('uploadForm');
const spinner = document.getElementById('spinner');

drop.addEventListener('dragover',  e => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => {
  e.preventDefault(); drop.classList.remove('drag');
  if (e.dataTransfer.files[0]) { inp.files = e.dataTransfer.files; submit(); }
});
inp.addEventListener('change', () => { if (inp.files[0]) submit(); });

function submit() {
  drop.style.display = 'none';
  spinner.style.display = 'block';
  form.submit();
}
</script>
</body>
</html>"""


@app.route('/')
def index():
    return LANDING_HTML


@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if not f:
        return '未找到檔案', 400
    try:
        content = f.read()
        data = parse_mtm_csv_v2(content)
        html = build_html(data)
        return html
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return f"""
        <html><body style="font-family:monospace;background:#0e0f11;color:#e8;padding:32px">
        <h2 style="color:#D85A30">解析錯誤</h2>
        <pre style="color:#7a7d87;font-size:12px;margin-top:16px">{tb}</pre>
        <a href="/" style="color:#8b9cf7">← 返回</a>
        </body></html>""", 500


if __name__ == '__main__':
    print("\n🚀 IB 結單儀表板已啟動")
    print("   請開啟瀏覽器訪問 http://localhost:5002\n")
    app.run(debug=True, host='0.0.0.0', port=5002)
