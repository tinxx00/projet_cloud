import pandas as pd
from sklearn.model_selection import train_test_split

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score


# Charger les données
DATA_PATH = 'data/processed_quotes.csv'
df = pd.read_csv(DATA_PATH)

# Afficher la distribution des classes
print('Distribution des classes direction :')
print(df['direction'].value_counts())



# La colonne cible est 'direction'. On ne garde que les colonnes numériques pour X.
from sklearn.preprocessing import LabelEncoder

y = df['direction']
# On encode la cible si besoin (ex: 'UP', 'DOWN' -> 0, 1)
le = LabelEncoder()
y = le.fit_transform(y)

# On sélectionne uniquement les colonnes numériques pour X
X = df.select_dtypes(include=['number'])

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)



# Entraînement du modèle Logistic Regression avec pondération des classes
model_lr = LogisticRegression(max_iter=1000, class_weight='balanced')
model_lr.fit(X_train, y_train)
y_pred_lr = model_lr.predict(X_test)

print('\n--- Logistic Regression ---')
print('Accuracy:', accuracy_score(y_test, y_pred_lr))
print('Classification report:')
print(classification_report(y_test, y_pred_lr))


# Entraînement du modèle Random Forest avec pondération des classes
model_rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model_rf.fit(X_train, y_train)
y_pred_rf = model_rf.predict(X_test)

print('\n--- Random Forest ---')
print('Accuracy:', accuracy_score(y_test, y_pred_rf))
print('Classification report:')
print(classification_report(y_test, y_pred_rf))
