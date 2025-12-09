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

```bash
python advanced_downloader.py
```

Files will be downloaded into a `downloads` folder.

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
advanced_downloader.py   -> Main script
README.md                -> Documentation
downloads/               -> Downloaded files (auto-created)
```

---

## Author

Isha Gupta
