def save_as_jsonl(data: str, file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)
        print(f"Data saved to {file_path} as JSONL.")


def save_as_csv(data: str, file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)
        print(f"Data saved to {file_path} as CSV.")
