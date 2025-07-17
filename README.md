# NBG Gravestone Pipeline

## About

This project was made in conjuction with Dr. Jordi Rivera and Providence's North Burial Ground.

Providence’s Northern Burial Ground (NBG) is unique in its size (100,000+) and longevity (in use since 1700). It contains valuable historical information about a large number of people who have lived and died in Providence. NBG is interested in telling the stories of all groups that are buried here, especially those whose stories have been historically ignored, altered, or undershared. Since NBG did not normalize data collection until 1848, one of the only ways to obtain important anthropological information is through the gravestones themselves, which are degrading due to weathering. This project aims to gather this anthropological information faster and more generally via a data science pipeline that is able to transcribe the textual and graphical information about the gravestone.

## How to Use

For now, run the code in the notebook called Claude.ipynb

**Note: Make sure your images are less than 5MB!**

1. You need an API key for Claude, which you can get here: https://www.anthropic.com/api
2. Place your API Key in a file called credentials.txt in the /notebooks folder.
3. Place images in data/input.
4. In the first couple cells, you can change your prompts, and the corresponding output columns. If you are adding prompts, make sure to add it to the list called PROMPTS, and add a corresponding column in COLUMNS in the correct order. 
5. Run the rest of the code blocks. You might have to pip install some of the packages imported, as I have not set up a config file yet.
6. Your output should be data/output!

