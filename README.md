# Fun With Text
This is kind of a silly application of a few things I wanted to learn about. It incorporates OpenAI, scraping of a Wikipedia page, and another student's microservice.

## But what does it do?
Well, it doesn't do anything too consequential: it gets a word or phrase, and returns a paragraph that links together three loosely-related words or concepts. 

## How does it work?
There are a few steps, mostly hidden:
-First, a user enters a word or phrase - it could be in English, French, Spanish, Chinese, or Hindi
- Next, the application searches Wikipedia for a page for that term
- It then calls a function that uses BeautifulSoup to find linked articles on that page, and returns three words / phrases at random from those links
- The microservice then searches Wikipedia (again!) for a page that contains those three terms, and returns the summary paragraph (if successful)
- The three terms are then sent to the OpenAI API, which returns a paragraph of text that relates the terms and the summary together with some theme, which in the current case is "pitch for a new startup."

## How could it be improved?
- use a regex to check for valid terms / phrases, both from the user and from Wiki parsing
- host it!
- find a good use case besides something silly
