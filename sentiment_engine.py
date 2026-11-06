from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize the analyzer once to save memory and speed up execution
analyzer = SentimentIntensityAnalyzer()

def get_headline_sentiment(headline: str) -> tuple[str, str]:
    """
    Evaluates financial headline text and returns a tuple:
    (Sentiment_Tag, CSS_Color_Class)
    """
    if not headline:
        return "NEUTRAL", "badge-grey"
        
    scores = analyzer.polarity_scores(headline)
    compound = scores['compound']
    
    # Financial thresholds: requires a stronger lean to trigger Bullish/Bearish
    if compound >= 0.15:
        return "BULLISH", "badge-green"
    elif compound <= -0.15:
        return "BEARISH", "badge-red"
    else:
        return "NEUTRAL", "badge-grey"
