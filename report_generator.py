import json


def generate_report():
    with open("crawl_data.json", "r", encoding="utf-8") as file:
        summary = json.load(file)

    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("CRAWLER REPORT\n\n")

        f.write("1. UNIQUE PAGES\n")
        f.write(f"{summary['unique_pages']}\n\n")

        f.write("2. LONGEST PAGE\n")
        longest = summary["longest_page"]
        f.write(f"URL: {longest['url']}\n")
        f.write(f"Word count: {longest['word_count']}\n\n")

        f.write("3. TOP 50 MOST COMMON WORDS\n")
        for word, count in summary["most_common_words"]:
            f.write(f"{word}, {count}\n")

        f.write("\n4. ICS SUBDOMAINS\n")

        subdomains = summary["ics_subdomains"]
        f.write(f"Total: {len(subdomains)}\n")

        for domain, count in sorted(subdomains):
            f.write(f"{domain}, {count}\n")

    print("Successfully generated report.txt")


if __name__ == "__main__":
    generate_report()