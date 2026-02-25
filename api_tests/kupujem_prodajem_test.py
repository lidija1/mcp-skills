import json
import pytest


@pytest.mark.api
def test_kupujem_stripove(api_session):
    url = "https://www.kupujemprodajem.com/api/web/v1/search"
    params = {'keywords': 'stripovi'}                    # We set the search keyword to 'stripovi' to search for comics on the website

    response = api_session.get(url, params=params)       # We send a GET request to the search endpoint with the keyword 'stripovi'
                                                         # to retrieve the search results for comics

    assert response.status_code == 200

    data = response.json()                                  # We parse the response as JSON to work with it as a Python dictionary
    # We are checking the structure of the response to understand where the ads are located
    results = data.get('results', {})                       # we use .get() to avoid KeyError if 'results' is not present

    # Extracting the ads from the results. The key might be 'ads' or something similar, we need to check the actual response structure.
    ads = results.get('ads', [])                            # we use .get() to avoid KeyError if 'ads' is not present
    print(f"\nOn the first page there is: {len(ads)} ads")  # we print the number of ads we got to verify that we are retrieving the correct data
                                                            # and to understand how many items we are working with
    print("-" * 40)

    # Printing the name and price of each ad to verify we are getting the correct data
    for i, ad in enumerate(ads, start=1):                   # we start enumeration at 1 for better readability
        comic_name = ad.get('name', 'N/A')                  # we use .get() to avoid KeyError if 'name' is not present
        price = ad.get('price', 'N/A')                      # we use .get() to avoid KeyError if 'price' is not present
        print(f"{i}. {comic_name} - Price: {price}")        # we print the index, name and price of each ad for better readability

    print("\n===== GET Response =====")
    print(json.dumps(data, indent=2))                       # we print the entire response in a pretty format to understand its structure
                                                            # and verify the data we are getting
