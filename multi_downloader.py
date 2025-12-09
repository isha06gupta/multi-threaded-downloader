import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def download_file(url, output_folder, retries=3):
    filename = url.split("/")[-1] or "downloaded_file"
    filepath = os.path.join(output_folder, filename)

    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, headers=HEADERS, timeout=10) as response:
                response.raise_for_status()

                total = int(response.headers.get('content-length', 0))
                chunk_size = 1024

                progress = tqdm(
                    total=total,
                    unit='B',
                    unit_scale=True,
                    desc=filename,
                    leave=True
                )

                start = time.time()

                with open(filepath, "wb") as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)
                            progress.update(len(chunk))

                progress.close()
                end = time.time()

                return (filename, True, round(end - start, 2))

        except Exception as e:
            print(f"[Attempt {attempt+1}] Failed to download {filename}: {e}")
            if attempt == retries - 1:
                return (filename, False, None)

    return (filename, False, None)


def multi_download(urls, output_folder="downloads", max_threads=3):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    results = []

    with ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {executor.submit(download_file, url, output_folder): url for url in urls}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Unexpected error downloading {url}: {e}")

    print("\n--- Download Summary ---")
    for filename, success, seconds in results:
        if success:
            print(f"{filename}: Downloaded successfully in {seconds} seconds")
        else:
            print(f"{filename}: Failed to download")


if __name__ == "__main__":
    urls = [
        "https://raw.githubusercontent.com/vinta/awesome-python/master/README.md",
        "https://raw.githubusercontent.com/TheAlgorithms/Python/master/README.md",
        "https://download.samplelib.com/mp4/sample-5s.mp4"
    ]

    multi_download(urls)
