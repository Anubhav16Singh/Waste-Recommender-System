import requests
from bs4 import BeautifulSoup

def get_product_recommendations(predicted_class):
    recommendations = []
    if predicted_class == 'Clothes':
        search_query = 'diy ideas to reuse or recycle'
        url = f"https://duckduckgo.com/html/?q={search_query}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', {'class': 'result__a'})
        
        for link in links[:5]:
            recommendations.append(link.get('href'))
    
    return recommendations
