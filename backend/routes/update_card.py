from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASS', 'password'),
    database=os.getenv('DB_NAME', 'Anki')
)
curr = conn.cursor()

@app.route('/update_card', methods=['POST'])
def update_card():
     data = request.get_json()
     card_id = data.get('card_id')
     q_value = data.get('q_value')
     if not card_id:
          return jsonify({'error': 'Card ID is required'}), 400
     if q_value is None:
          return jsonify({'error': 'Q-value is required'}), 400
     try:
          query = "SELECT intervalLength, cardEase, repetitions, deckID FROM Cards WHERE cardID = %s"
          curr.execute(query, (card_id,))
          card = curr.fetchone()
          if not card:
               return jsonify({'error': 'Card not found'}), 404
          interval_length, card_ease, repetitions, deck_id = card

          # Implementing the SM2 algorithm
          if q_value < 3:  # If the answer is low performance
               repetitions = 0
               interval_length = 0  # Reset interval for low performance
               card_ease = max(1.3, card_ease - 0.2)  # Decrease ease
          else:
               if repetitions == 0:
                    interval_length = 1
               elif repetitions == 1:
                    interval_length = 3
               else:
                    interval_length = round(interval_length * card_ease)
               repetitions += 1
               card_ease = min(2.5, card_ease + 0.1 if q_value > 3 else card_ease - 0.2)

          # Update card in database
          update_query = """
          UPDATE Cards 
          SET intervalLength = %s, cardEase = %s, repetitions = %s, previousReviewDate = CURDATE() 
          WHERE cardID = %s
          """
          curr.execute(update_query, (interval_length, card_ease, repetitions, card_id))
          conn.commit()

          # Update UserStats (optional)
          user_id_query = "SELECT UserId FROM Decks WHERE DeckId = %s"
          curr.execute(user_id_query, (deck_id,))
          user_id = curr.fetchone()[0]

          update_user_stats_query = """
          UPDATE UserStats 
          SET learningPace = learningPace + 1, deckCount = deckCount + 1 
          WHERE userId = %s
          """
          curr.execute(update_user_stats_query, (user_id,))
          conn.commit()

          return jsonify({
               'message': 'Card updated successfully!',
               'cardID': card_id,
               'newIntervalLength': interval_length,
               'newCardEase': card_ease,
               'newRepetitions': repetitions
          }), 200
     except mysql.connector.Error as err:
          return jsonify({'error': str(err)}), 500

if __name__ == '__main__':
     app.run(host='127.0.0.1', port=5000, debug=True)
