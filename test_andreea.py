import requests

res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "DSyEqotpot7tSPibliSfLw", "isbns": "0553803700"})
if res.status_code == 404:
  print("error")
else:
  rezultat = res.json()
  no_reviews = rezultat['books'][0]['work_ratings_count']
  average_rating = rezultat['books'][0]['average_rating']
 

  print(no_reviews)
  print(type(average_rating))


# 40231696

  # book = db.execute("""SELECT books.title, books.author, books.year, books.isbn, COUNT(reviews.rating) AS no_reviews, 
    #                             AVG(reviews.rating) AS avg_rating FROM books INNER JOIN reviews ON books.book_id = reviews.book_id
    #                             WHERE books.isbn = :isbn GROUP BY title, author, year, isbn;""", {"isbn": isbn_number}).fetchone()
    
