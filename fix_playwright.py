import re

with open('frontend/playwright.config.js', 'r') as f:
    content = f.read()

# We need to temporarily comment out webserver to let playwright skip backend check
content = re.sub(r'  webServer: \[.*?\],', '', content, flags=re.DOTALL)
with open('frontend/playwright.config.js', 'w') as f:
    f.write(content)
