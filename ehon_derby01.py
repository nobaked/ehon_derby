import streamlit as st
import pandas as pd
import requests
import json
import time
import urllib.parse
import os
from dotenv import load_dotenv

# CSVファイルのパスを指定
csv_file_path = "output_with_all_keywords_update.csv"

# CSVファイルを読み込む
try:
    df = pd.read_csv(csv_file_path)
except FileNotFoundError:
    st.error(f"CSVファイル '{csv_file_path}' が見つかりません。正しいパスを設定してください。")
    st.stop()



# --- 環境変数の読み込み ---
load_dotenv()

# --- APIキー取得 ---
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
CALIL_API_KEY = os.getenv("CALIL_API_KEY")

# --- Perplexity APIからやさしい解説を取得する関数 ---
def get_summary_from_perplexity(title, author, retries=3, delay=2):
    prompt = f"次の絵本のやさしい紹介文を200文字以内で書いてください：『{title}』（著者：{author}）"
    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json; charset=utf-8"  # UTF-8を明示的に指定
    }

    data = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    for attempt in range(retries):
        try:
            # ensure_ascii=Falseを指定してUnicodeをそのまま使用する
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            response = requests.post(url, headers=headers, data=json_data)
            response.raise_for_status()

            json_response = response.json()
            return json_response["choices"][0]["message"]["content"].strip()

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)
                print(f"リトライ中... ({attempt + 1}/{retries})")
            else:
                print(f"Perplexity APIエラー: {e}")
                return f"（解説を取得できませんでした: {str(e)}）"
        except (KeyError, ValueError) as e:
            print(f"JSONエラー: {e}")
            return f"（JSONの解析に失敗しました: {str(e)}）"

# --- Perplexity APIから正確なISBNを取得する関数 ---
def get_isbn_from_perplexity(title, author, retries=3, delay=2):
    prompt = f"次の絵本『{title}』（著者：{author}）のISBN番号を教えてください。回答はISBN番号のみを返してください。複数ある場合は最新版のものを返してください。"
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json; charset=utf-8"  # UTF-8を明示的に指定
    }

    data = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3  # より正確な結果を得るために低い温度を設定
    }

    for attempt in range(retries):
        try:
            # ensure_ascii=Falseを指定してUnicodeをそのまま使用する
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            response = requests.post(url, headers=headers, data=json_data)
            response.raise_for_status()

            json_response = response.json()
            isbn_response = json_response["choices"][0]["message"]["content"].strip()
            
            # ISBNだけを抽出（数字のみを取り出す）
            import re
            isbn_match = re.search(r'(?:ISBN[-]?1[03]?:?\s*)?(?=[0-9X]{10}|(?=(?:[0-9]+[-\s]){3})[-\s0-9X]{13}|97[89][0-9]{10}|(?=(?:[0-9]+[-\s]){4})[-\s0-9]{17})(?:97[89][-\s]?)?[0-9]{1,5}[-\s]?[0-9]+[-\s]?[0-9]+[-\s]?[0-9X]', isbn_response)
            
            if isbn_match:
                isbn = re.sub(r'[^0-9X]', '', isbn_match.group(0))
                return isbn
            else:
                # ISBNが見つからない場合は、レスポンスから数字だけを抽出してみる
                numbers_only = re.sub(r'[^0-9]', '', isbn_response)
                if len(numbers_only) >= 10:  # 少なくとも10桁あればISBNっぽい
                    return numbers_only[:13] if len(numbers_only) >= 13 else numbers_only[:10]
                else:
                    print(f"有効なISBNが見つかりませんでした。レスポンス: {isbn_response}")
                    if attempt < retries - 1:
                        continue
                    return None

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)
                print(f"リトライ中... ({attempt + 1}/{retries})")
            else:
                print(f"Perplexity APIエラー: {e}")
                return None
        except (KeyError, ValueError) as e:
            print(f"JSONエラー: {e}")
            return None
    
    return None

# --- Perplexity APIから図書館の詳細情報を取得する関数 ---
def get_library_info_from_perplexity(title, author, prefecture, retries=3, delay=2):
    prompt = f"絵本『{title}』（著者：{author}）が{prefecture}の図書館で借りられるかを調べたいです。{prefecture}の代表的な公共図書館の名前と公式URLを3つ程度教えてください。マークダウン形式でリンク付きで回答してください。"
    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json; charset=utf-8"
    }

    data = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    for attempt in range(retries):
        try:
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            response = requests.post(url, headers=headers, data=json_data)
            response.raise_for_status()

            json_response = response.json()
            return json_response["choices"][0]["message"]["content"].strip()

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)
                print(f"リトライ中... ({attempt + 1}/{retries})")
            else:
                print(f"Perplexity APIエラー: {e}")
                return None
        except (KeyError, ValueError) as e:
            print(f"JSONエラー: {e}")
            return None

# カーリルAPIを使って図書館を直接検索する関数
def search_libraries_by_isbn(isbn, pref):
    # ステップ1: 都道府県内の図書館一覧を取得
    try:
        lib_resp = requests.get(
            "https://api.calil.jp/library",
            params={"appkey": CALIL_API_KEY, "pref": pref, "format": "json", "callback": "no"}
        )
        libraries = lib_resp.json()
        
        if not libraries:
            st.warning("この都道府県には対応図書館がありません。")
            return False
        
        # 図書館のシステムIDを抽出
        systemids = list(set([lib["systemid"] for lib in libraries]))
        
        # ステップ2: 指定ISBNの蔵書状況を確認
        check_resp = requests.get(
            "https://api.calil.jp/check",
            params={
                "appkey": CALIL_API_KEY,
                "isbn": isbn,
                "systemid": ",".join(systemids),
                "format": "json",
                "callback": "no"
            }
        )
        check_data = check_resp.json()
        
        # セッションIDを取得してポーリング
        session = check_data.get("session", "")
        
        # 処理中フラグ
        continue_polling = True
        max_attempts = 10
        attempt = 0
        
        # すべての結果が処理されるまでポーリング
        while continue_polling and attempt < max_attempts:
            time.sleep(1)  # 1秒待機
            poll_resp = requests.get(
                "https://api.calil.jp/check",
                params={
                    "appkey": CALIL_API_KEY, 
                    "session": session,
                    "format": "json",
                    "callback": "no"
                }
            )
            poll_data = poll_resp.json()
            
            # 処理状況を確認
            continue_polling = poll_data.get("continue", 0) == 1
            attempt += 1
            
            # 結果を更新
            if "books" in poll_data and isbn in poll_data["books"]:
                check_data["books"][isbn].update(poll_data["books"][isbn])
        
        # 結果を表示
        found = False
        if "books" in check_data and isbn in check_data["books"]:
            result_container = st.container()
            
            with result_container:
                st.subheader("蔵書検索結果")
                
                # 貸出可・蔵書ありの図書館を優先表示
                available_libs = []
                unavailable_libs = []
                
                for sysid, sys_result in check_data["books"][isbn].items():
                    if sys_result.get("status") == "OK":
                        libkey = sys_result.get("libkey", {})
                        system_name = next((lib["systemname"] for lib in libraries if lib["systemid"] == sysid), sysid)
                        
                        for libname, status in libkey.items():
                            if status in ["貸出可", "蔵書あり"]:
                                available_libs.append((system_name, libname, status))
                                found = True
                            elif status not in ["Error", "蔵書なし"]:
                                unavailable_libs.append((system_name, libname, status))
                
                # 貸出可能な図書館があれば表示
                if available_libs:
                    st.success("貸出可能な図書館が見つかりました！")
                    for system_name, libname, status in available_libs:
                        st.info(f"📚 {libname}（{system_name}）: **{status}**")
                
                # 貸出中などの図書館も表示
                if unavailable_libs:
                    st.info("以下の図書館でも蔵書がありますが、現在貸出中などの状態です：")
                    for system_name, libname, status in unavailable_libs:
                        st.warning(f"📚 {libname}（{system_name}）: **{status}**")
                
                # 図書館が見つからない場合
                if not found and not unavailable_libs:
                    st.warning("この本を所蔵している図書館は見つかりませんでした。")
                    return False
                
                return True
        
        # 結果がない場合
        if not found:
            st.warning("この本を所蔵している図書館は見つかりませんでした。")
            return False
            
    except Exception as e:
        st.error(f"図書館検索中にエラーが発生しました: {str(e)}")
        return False

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = "search"  # "search" または "library"
if 'search_initiated' not in st.session_state:
    st.session_state.search_initiated = False
if 'selected_books' not in st.session_state:
    st.session_state.selected_books = []
if 'library_search_initiated' not in st.session_state:
    st.session_state.library_search_initiated = False
if 'corrected_isbn' not in st.session_state:
    st.session_state.corrected_isbn = None
if 'search_result' not in st.session_state:
    st.session_state.search_result = None
if 'book_summaries' not in st.session_state:
    st.session_state.book_summaries = {}

# 本を選択した時の処理
def select_book(isbn, title, author):
    st.session_state.selected_books = [(isbn, title, author)]
    st.session_state.page = "library"  # 図書館検索ページに切り替え
    st.session_state.library_search_initiated = False
    st.session_state.corrected_isbn = None
    st.session_state.search_result = None

# 絵本検索ページ
def show_book_search_page():
    st.title("📚 楽しい絵本を見つけよう！")
    st.write("こんにちは！絵本の中から、どんなお話が気になるかな？")

    # --- キーワード選択 ---
    keywords = ["どうぶつ", "きょうりゅう", "いぬ", "ねこ", "のりもの", "むし", "おばけ", "あんぱんまん", "そら", "まほう"]
    additional_keywords = ["わくわく", "どきどき", "いらいら", "きらきら", "楽しい", "かわいい", "シリーズ", "世界", "もの", "シール", "登場"]

    col1, col2 = st.columns(2)
    with col1:
        selected_keyword1 = st.selectbox("絵本に出てくるキャラクターやテーマを選ぼう！", keywords)
    with col2:
        selected_keyword2 = st.selectbox("どんな気持ちが出てくる絵本が良いかな？", additional_keywords)

    # 検索ボタン
    if st.button("絵本を探す！"):
        st.session_state.search_initiated = True
        # 選択された本をリセット
        st.session_state.selected_books = []
        st.session_state.library_search_initiated = False
        st.session_state.corrected_isbn = None
        st.session_state.search_result = None
        st.rerun()  # この行を追加: ページを強制的に再読み込み

    if st.session_state.search_initiated:
        # キーワードフィルタリングの条件
        if selected_keyword1 in df.columns and selected_keyword2 in df.columns:
            filtered_df = df[(df[selected_keyword1] == 1) & (df[selected_keyword2] == 1)]

            if not filtered_df.empty:
                # 上位20件を抽出（多すぎる場合はavailable分に調整）
                top_candidates = filtered_df.sort_values(by='reviewAverage', ascending=False).head(30)

                # その中からランダムに5件選ぶ（少なければ全て）
                top_5_recommended = top_candidates.sample(n=min(5, len(top_candidates)), random_state=None)

                st.write("---")
                st.subheader("👇 見つかった絵本だよ！")
                st.write(f"「{selected_keyword1}」と「{selected_keyword2}」がテーマの絵本が見つかったよ！✨")

                for idx, row in top_5_recommended.iterrows():
                    with st.container():
                        cols = st.columns([1, 3])
                        
                        with cols[0]:
                            if 'largeImageUrl' in row and pd.notna(row['largeImageUrl']):
                                st.image(row['largeImageUrl'], width=150)
                            else:
                                st.write("画像がありません")
                        
                        with cols[1]:
                            st.markdown(f"### {row['title']}")
                            st.write(f"**著者**: {row['author']}")
                            st.write(f"**出版社**: {row['publisherName']}")
                            st.write(f"**価格**: {row['itemPrice']}円")
                            st.write(f"**発売日**: {row['salesDate']}")
                            st.write(f"**レビュー**: {row['reviewAverage']}点")

                            # 既にサマリーがキャッシュされているか確認
                            book_key = f"{row['title']}_{row['author']}"
                            if book_key not in st.session_state.book_summaries:
                                # 初めて表示する本の場合、解説を取得してキャッシュ
                                explanation = get_summary_from_perplexity(row['title'], row['author'])
                                st.session_state.book_summaries[book_key] = explanation
                            else:
                                # キャッシュから解説を取得
                                explanation = st.session_state.book_summaries[book_key]
                            
                            st.info(f"📘 解説: {explanation}")

                            st.write(f"[楽天ブックスで見る]({row['itemUrl']})")

                            if st.button(f"📖 この本で図書館を探す", key=f"select_{row['isbn']}_{idx}"):
                                select_book(row['isbn'], row['title'], row['author'])
                                st.rerun()

                    st.write("---")
            else:
                st.warning("ごめんね、選んだキーワードに合う絵本が見つからなかったよ。別のキーワードで試してみよう！")
        else:
            st.warning("選んだキーワードがデータにないみたい。別のキーワードで試してみてね！")

# 図書館検索ページ
def show_library_search_page():
    if st.session_state.selected_books:
        isbn, title, author = st.session_state.selected_books[0]
        
        st.title("📚 図書館で絵本を探そう！")
        
        # 選択した本の情報を上部に表示
        book_info = df[df['isbn'] == isbn]
        if not book_info.empty:
            row = book_info.iloc[0]
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    if 'largeImageUrl' in row and pd.notna(row['largeImageUrl']):
                        st.image(row['largeImageUrl'], width=150)
                    else:
                        st.write("画像がありません")
                
                with col2:
                    st.markdown(f"## 『{title}』")
                    st.write(f"**著者**: {author}")
                    if 'publisherName' in row:
                        st.write(f"**出版社**: {row['publisherName']}")
                    if 'itemPrice' in row:
                        st.write(f"**価格**: {row['itemPrice']}円")
                    if 'salesDate' in row:
                        st.write(f"**発売日**: {row['salesDate']}")
                    if 'reviewAverage' in row:
                        st.write(f"**レビュー**: {row['reviewAverage']}点")
                    
                    # 本のURL（楽天）
                    if 'itemUrl' in row:
                        st.write(f"[楽天ブックスで見る]({row['itemUrl']})")
                        
                    # 解説の表示
                    book_key = f"{title}_{author}"
                    if book_key in st.session_state.book_summaries:
                        explanation = st.session_state.book_summaries[book_key]
                        st.info(f"📘 解説: {explanation}")
        
        st.write("この本が近くの図書館にあるか調べてみよう！")
        
        # 都道府県選択
        pref_list = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
            "岐阜県", "静岡県", "愛知県", "三重県",
            "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
            "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県",
            "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        selected_pref_name = st.selectbox("お住まいの都道府県を選んでください", pref_list)
        
        # 図書館検索ボタン
        if st.button("🔍 近くの図書館で検索！"):
            st.session_state.library_search_initiated = True
            st.rerun()
        
        # 図書館検索が開始された場合
        if st.session_state.library_search_initiated:
            with st.spinner(f"『{title}』を{selected_pref_name}の図書館で検索中..."):
                # まだISBNが修正されていない場合は、Perplexityで正確なISBNを取得
                if st.session_state.corrected_isbn is None:
                    with st.spinner(f"正確なISBNを検索中..."):
                        st.session_state.corrected_isbn = get_isbn_from_perplexity(title, author)

                
                # 取得したISBNで図書館検索
                search_isbn = st.session_state.corrected_isbn or isbn
                st.session_state.search_result = search_libraries_by_isbn(search_isbn, selected_pref_name)
                
                # 検索結果へのカーリルリンクも表示
                base_url = "https://calil.jp/book/"
                encoded_pref = urllib.parse.quote(selected_pref_name)
                calil_url = f"{base_url}{search_isbn}/search?pref={encoded_pref}"
                
                # Perplexityを使って図書館のURL情報を取得
                with st.spinner("図書館の詳細情報を取得中..."):
                    library_info = get_library_info_from_perplexity(title, author, selected_pref_name)
                    if library_info:
                        st.markdown(f"### {selected_pref_name}の主な図書館")
                        st.markdown(library_info)
                
                st.markdown(f"より詳しい検索結果は[カーリルのサイト]({calil_url})で確認できます。")
                st.info("本を借りるときは、図書館カードが必要です。お近くの図書館に行ってみてね！")
        
        # 別の本を探すボタン
        if st.button("🔄 別の絵本を探す"):
            st.session_state.page = "search"
            st.session_state.selected_books = []
            st.session_state.library_search_initiated = False
            st.session_state.corrected_isbn = None
            st.session_state.search_result = None
            st.rerun()  # ページ遷移時に確実に再読み込みする

# メインアプリ
def main():
    # ページに応じて表示を切り替え
    if st.session_state.page == "search":
        show_book_search_page()
    elif st.session_state.page == "library":
        show_library_search_page()

if __name__ == "__main__":
    main()