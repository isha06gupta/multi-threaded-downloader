import os
import json
import argparse
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_file_info(url):
    response = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    accept_ranges = response.headers.get("accept-ranges", "").lower()

    if accept_ranges == "bytes" and total_size > 0:
        return total_size, True

    headers = HEADERS.copy()
    headers["Range"] = "bytes=0-0"
    with requests.get(url, headers=headers, stream=True, timeout=10) as range_response:
        if range_response.status_code == 206:
            content_range = range_response.headers.get("content-range", "")
            if "/" in content_range:
                total_size = int(content_range.split("/")[-1])
            return total_size, total_size > 0

    return total_size, False


def split_ranges(total_size, chunk_count):
    chunk_count = max(1, min(chunk_count, total_size))
    chunk_size = total_size // chunk_count
    ranges = []

    start = 0
    for index in range(chunk_count):
        end = total_size - 1 if index == chunk_count - 1 else start + chunk_size - 1
        ranges.append((start, end))
        start = end + 1

    return ranges


def metadata_path_for(filepath):
    return f"{filepath}.meta"


def load_metadata(meta_path):
    try:
        with open(meta_path, "r", encoding="utf-8") as meta_file:
            metadata = json.load(meta_file)
        ranges = [tuple(byte_range) for byte_range in metadata["ranges"]]
        return metadata["total_size"], ranges
    except Exception as e:
        print(f"Ignoring corrupted metadata {meta_path}: {e}")
        return None, None


def save_metadata(meta_path, total_size, ranges):
    metadata = {
        "total_size": total_size,
        "ranges": ranges
    }
    with open(meta_path, "w", encoding="utf-8") as meta_file:
        json.dump(metadata, meta_file)


def get_part_status(part_path, byte_range):
    expected_size = byte_range[1] - byte_range[0] + 1
    current_size = os.path.getsize(part_path) if os.path.exists(part_path) else 0

    if current_size > expected_size:
        os.remove(part_path)
        current_size = 0

    return current_size, expected_size


def download_chunk(url, part_path, byte_range, progress, retries=3):
    range_start, range_end = byte_range
    initial_size, expected_size = get_part_status(part_path, byte_range)
    progress.update(initial_size)

    for attempt in range(retries):
        try:
            current_size, expected_size = get_part_status(part_path, byte_range)
            if current_size == expected_size:
                return True

            start = range_start + current_size
            end = range_end
            headers = HEADERS.copy()
            headers["Range"] = f"bytes={start}-{end}"

            with requests.get(url, headers=headers, stream=True, timeout=10) as response:
                response.raise_for_status()
                if response.status_code != 206:
                    raise RuntimeError("Server did not return partial content")

                with open(part_path, "ab") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            progress.update(len(chunk))

                final_size, _ = get_part_status(part_path, byte_range)
                if final_size == expected_size:
                    return True
                raise RuntimeError("Chunk finished with incomplete size")
        except Exception as e:
            print(f"[Attempt {attempt+1}] Failed chunk {range_start}-{range_end}: {e}")
            if attempt == retries - 1:
                return False

    return False


def merge_chunks(filepath, part_paths):
    with open(filepath, "wb") as output_file:
        for part_path in part_paths:
            with open(part_path, "rb") as part_file:
                while True:
                    chunk = part_file.read(1024 * 1024)
                    if not chunk:
                        break
                    output_file.write(chunk)

    for part_path in part_paths:
        os.remove(part_path)


def download_file_single_threaded(url, output_folder, retries=3):
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


def download_file(url, output_folder, chunk_count=4, max_threads=4, retries=3):
    filename = url.split("/")[-1] or "downloaded_file"
    filepath = os.path.join(output_folder, filename)

    try:
        total_size, supports_ranges = get_file_info(url)
    except Exception as e:
        print(f"Could not detect range support for {filename}: {e}")
        return download_file_single_threaded(url, output_folder, retries)

    if not supports_ranges:
        print(f"{filename}: Range requests not supported, using single-threaded download")
        return download_file_single_threaded(url, output_folder, retries)

    meta_path = metadata_path_for(filepath)
    saved_total_size, saved_ranges = load_metadata(meta_path) if os.path.exists(meta_path) else (None, None)
    if saved_total_size == total_size and saved_ranges:
        ranges = saved_ranges
    else:
        ranges = split_ranges(total_size, chunk_count)
        save_metadata(meta_path, total_size, ranges)

    part_paths = [f"{filepath}.part{index}" for index in range(len(ranges))]
    progress = tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, leave=True)
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_threads) as executor:
            future_to_part = {
                executor.submit(download_chunk, url, part_paths[index], byte_range, progress, retries): part_paths[index]
                for index, byte_range in enumerate(ranges)
            }

            for future in as_completed(future_to_part):
                if not future.result():
                    raise RuntimeError("One or more chunks failed")

        merge_chunks(filepath, part_paths)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        end_time = time.time()
        return (filename, True, round(end_time - start_time, 2))
    except Exception as e:
        print(f"Failed segmented download for {filename}: {e}")
        return (filename, False, None)
    finally:
        progress.close()


def multi_download(urls, output_folder="downloads", max_threads=3, chunk_count=4, retries=3):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    results = []

    with ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {
            executor.submit(download_file, url, output_folder, chunk_count, max_threads, retries): url
            for url in urls
        }

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


def positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value} is not a valid integer")

    if number < 1:
        raise argparse.ArgumentTypeError("value must be greater than 0")

    return number


def load_urls_from_file(urls_file):
    if not os.path.exists(urls_file):
        raise argparse.ArgumentTypeError(f"URL file does not exist: {urls_file}")

    with open(urls_file, "r", encoding="utf-8") as file:
        urls = [line.strip() for line in file if line.strip() and not line.strip().startswith("#")]

    if not urls:
        raise argparse.ArgumentTypeError("URL file does not contain any URLs")

    return urls


def validate_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise argparse.ArgumentTypeError(f"Invalid URL: {url}")
    return url


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download files with segmented multi-threaded downloads and resume support."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", help="Single URL to download")
    source_group.add_argument("--urls-file", help="Text file containing one URL per line")
    parser.add_argument("--output", default="downloads", help="Download directory")
    parser.add_argument("--threads", type=positive_int, default=3, help="Maximum worker threads")
    parser.add_argument("--chunks", type=positive_int, default=4, help="Chunk count for segmented downloads")
    parser.add_argument("--retries", type=positive_int, default=3, help="Retry count")
    args = parser.parse_args()

    try:
        urls = [args.url] if args.url else load_urls_from_file(args.urls_file)
        args.urls = [validate_url(url) for url in urls]
    except argparse.ArgumentTypeError as e:
        parser.error(str(e))

    return args


if __name__ == "__main__":
    args = parse_args()
    multi_download(
        args.urls,
        output_folder=args.output,
        max_threads=args.threads,
        chunk_count=args.chunks,
        retries=args.retries
    )
