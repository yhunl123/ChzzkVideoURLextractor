import tkinter as tk
from tkinter import scrolledtext
import requests
import json
import re
import threading

# =========================================================
# [설정] 로그인이 필요한 영상(19세/유료)인 경우 아래에 쿠키를 입력하세요.
# 필요 없다면 빈 따옴표("")로 두시면 됩니다.
# =========================================================
USER_NID_AUT = ""
USER_NID_SES = ""
# =========================================================

class ChzzkExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("치지직 다시보기 URL 추출기")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # 스타일 설정
        label_font = ("Malgun Gothic", 10, "bold")
        entry_font = ("Malgun Gothic", 10)

        # 1. URL 입력 섹션
        tk.Label(root, text="치지직 다시보기 영상 URL", font=label_font, fg="#00C73C").pack(pady=(20, 5), anchor="w", padx=20)

        self.entry_url = tk.Entry(root, font=entry_font, width=55)
        self.entry_url.pack(pady=5, padx=20)
        # 힌트 텍스트 (클릭 시 사라짐 기능은 복잡해지므로 생략, 기본값 비워둠)

        # 2. 실행 버튼
        self.btn_extract = tk.Button(root, text="M3U8 주소 추출하기", command=self.start_extraction,
                                     bg="#00C73C", fg="white", font=("Malgun Gothic", 12, "bold"), height=2, cursor="hand2")
        self.btn_extract.pack(pady=15, fill="x", padx=20)

        # 3. 결과 출력 섹션
        tk.Label(root, text="추출 결과", font=label_font).pack(pady=(10, 5), anchor="w", padx=20)
        self.text_result = scrolledtext.ScrolledText(root, height=8, width=55, state="disabled", font=("Consolas", 9))
        self.text_result.pack(padx=20, pady=5)

        # 4. 복사 버튼
        self.btn_copy = tk.Button(root, text="URL 복사하기", command=self.copy_to_clipboard, state="disabled",
                                  font=("Malgun Gothic", 10), cursor="hand2")
        self.btn_copy.pack(pady=10)

        # 5. 상태 표시줄 (알림창 대체)
        self.lbl_status = tk.Label(root, text="준비됨", bd=1, relief="sunken", anchor="w", fg="gray", bg="#f0f0f0", padx=5)
        self.lbl_status.pack(side="bottom", fill="x")

    def set_status(self, message, color="black"):
        """상태 표시줄 업데이트"""
        self.lbl_status.config(text=message, fg=color)
        self.root.update_idletasks()

    def start_extraction(self):
        """별도 스레드에서 추출 시작"""
        url = self.entry_url.get().strip()

        if not url or "chzzk" not in url:
            self.set_status("⚠️ 올바른 치지직 URL을 입력해주세요.", "red")
            return

        # UI 초기화 및 잠금
        self.btn_extract.config(state="disabled", text="추출 중...")
        self.btn_copy.config(state="disabled")
        self.text_result.config(state="normal")
        self.text_result.delete(1.0, tk.END)
        self.text_result.config(state="disabled")
        self.set_status("⏳ 영상 정보를 분석하고 있습니다...", "blue")

        # 스레드 실행
        threading.Thread(target=self.run_logic, args=(url,), daemon=True).start()

    def run_logic(self, url):
        """실제 API 호출 로직"""
        try:
            video_id = self.get_video_id(url)

            if not video_id:
                raise Exception("URL에서 videoId를 찾을 수 없습니다.")

            # API 요청 준비
            api_url = f"https://api.chzzk.naver.com/service/v3/videos/{video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://chzzk.naver.com/",
                "Content-Type": "application/json"
            }

            cookies = {}
            # 코드 상단의 전역 변수 사용
            if USER_NID_AUT and USER_NID_SES:
                cookies = {"NID_AUT": USER_NID_AUT, "NID_SES": USER_NID_SES}

            # API 호출
            response = requests.get(api_url, headers=headers, cookies=cookies, timeout=10)

            if response.status_code != 200:
                raise Exception(f"서버 응답 오류: {response.status_code}")

            data = response.json()

            if data.get('code') != 200:
                msg = data.get('message', '알 수 없는 오류')
                raise Exception(f"API 오류: {msg}")

            # 이중 JSON 파싱
            content = data.get('content', {})
            video_title = content.get('videoTitle', '제목 없음')
            playback_json_str = content.get('liveRewindPlaybackJson')

            if not playback_json_str:
                raise Exception("영상 정보가 없습니다. (권한 부족 또는 삭제됨)")

            playback_data = json.loads(playback_json_str)
            media_list = playback_data.get('media', [])

            if not media_list:
                raise Exception("재생 가능한 미디어 경로가 없습니다.")

            # 결과 추출 (보통 첫 번째 요소의 path)
            m3u8_url = media_list[0].get('path')

            # UI 업데이트 (성공)
            self.root.after(0, lambda: self.show_success(video_title, m3u8_url))

        except Exception as e:
            # UI 업데이트 (실패)
            self.root.after(0, lambda: self.show_error(str(e)))

    def get_video_id(self, url):
        pattern = r"video\/([a-zA-Z0-9]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def show_success(self, title, url):
        """성공 시 결과창 업데이트"""
        self.text_result.config(state="normal")
        self.text_result.insert(tk.END, f"# 제목: {title}\n")
        self.text_result.insert(tk.END, url)
        self.text_result.config(state="disabled")

        self.btn_extract.config(state="normal", text="M3U8 주소 추출하기")
        self.btn_copy.config(state="normal")
        self.set_status(f"✅ 추출 성공! ({title})", "green")

    def show_error(self, error_msg):
        """실패 시 결과창 업데이트"""
        self.text_result.config(state="normal")
        self.text_result.insert(tk.END, f"[오류 발생]\n{error_msg}")
        self.text_result.config(state="disabled")

        self.btn_extract.config(state="normal", text="M3U8 주소 추출하기")
        self.set_status("❌ 추출 실패. 내용을 확인하세요.", "red")

    def copy_to_clipboard(self):
        """결과 텍스트(URL) 복사 및 상태바 알림"""
        # 첫 번째 줄(제목)을 제외하고 URL만 복사하도록 처리
        content = self.text_result.get("2.0", tk.END).strip()

        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.set_status("📋 클립보드에 URL이 복사되었습니다.", "blue")
        else:
            self.set_status("⚠️ 복사할 URL이 없습니다.", "red")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChzzkExtractorGUI(root)
    root.mainloop()