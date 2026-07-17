import re

def create_hyperlinks(raw_html_list):
    base_url = "https://nalayiram.in/index.php?padhamPrefix="
    hyperlinks = []

    for item in raw_html_list:
        # Extract content between <li> and </li>
        match = re.search(r'<li>(.*?)</li>', item)
        if match:
            content = match.group(1)  # This captures the text inside <li>

            # Split by the first space to separate the numbers and Tamil phrase
            parts = content.split(' ', 1)
            
            if len(parts) > 1:
                tamil_phrase = parts[1].strip()  # Get the Tamil phrase

                # Remove anything after the opening parenthesis
                tamil_phrase = re.sub(r'\(.*?\)', '', tamil_phrase).strip()

                # Replace spaces with '+' for URL encoding
                tamil_phrase_url = tamil_phrase.replace(' ', '+')

                # Rebuild the full HTML hyperlink, keeping the original <li> structure
                hyperlink = f'<li><a href="{base_url}{tamil_phrase_url}">{content}</a></li>'
                hyperlinks.append(hyperlink)

    return hyperlinks

# Input raw HTML list as text
input_text = """

                 <li>10-1 தாளதாமரை(3667-3677)</li>
                <li>10-2 கெடுமிடராய(3678-3688)</li>
                <li>10-3 வேய்மருதோளி(3689-3699)</li>
                <li>10-4 சார்வேதவநெறி(3700-3710)</li>
                <li>10-5 கண்ணன்கழலி(3711-3721)</li>
                <li>10-6 அருள் பெறுவார்(3722-3732)</li>
                <li>10-7 செங்சொற் கவி(3733-3743)</li>
                <li>10-8 திருமாலிருஞ்சோலை(3744-3754)</li>
                <li>10-9 சூழ்விசும்(3755-3765)</li>
                <li>10-10 முனியே நான்முகனே	(3766-3776)</li>
              <li>1-1 வாடினேன்வாடி(948-957)</li>

"""

# Convert the multiline string into a list of items
raw_html_list = input_text.strip().split('\n')

# Call the function and generate hyperlinks
hyperlinks = create_hyperlinks(raw_html_list)

# Print the hyperlinks
for link in hyperlinks:
    print(link)

