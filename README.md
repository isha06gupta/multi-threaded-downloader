# Multi-Threaded Downloader (Python)

A high-performance multi-threaded file downloader built using Python.  
This project uses `ThreadPoolExecutor`, retry logic, time measurement, and tqdm progress bars to provide clean and efficient parallel downloads.

---

## Features

- Multi-threaded downloads using ThreadPoolExecutor  
- Automatic retries on failure  
- Live progress bars using tqdm  
- Download time measurement per file  
- Custom request headers to avoid 403/SSL issues  
- Graceful error handling  
- Automatic output folder creation  

---

## Installation

Install required dependencies:

```bash
pip install requests tqdm
```

---

## Usage

Download one URL:

```bash
python multi_downloader.py --url https://example.com/file.zip
```

Download multiple URLs from a text file:

```bash
python multi_downloader.py --urls-file urls.txt
```

Use a custom output folder, thread count, chunk count, and retry count:

```bash
python multi_downloader.py --url https://example.com/file.zip --output downloads --threads 8 --chunks 4 --retries 5
```

Files will be downloaded into a `downloads` folder.

`urls.txt` should contain one URL per line. Blank lines and lines starting with `#` are ignored.

---

## CLI Options

```text
--url URL             Single URL to download
--urls-file PATH      Text file containing one URL per line
--output PATH         Download directory (default: downloads)
--threads N           Maximum worker threads (default: 3)
--chunks N            Chunk count for segmented downloads (default: 4)
--retries N           Retry count (default: 3)
```

---

## Sample Output

```
README.md: 100%|███████████████████████████| 80.0k/80.0k
sample-5s.mp4: 100%|███████████████████████| 2.85M/2.85M

--- Download Summary ---
README.md: Downloaded successfully in 0.02 seconds
sample-5s.mp4: Downloaded successfully in 1.21 seconds
```

---

## Project Structure

```
multi_downloader.py      -> Main script
README.md                -> Documentation
downloads/               -> Downloaded files (auto-created)
```

---

## Author

Isha Gupta
