-- Schéma de la base de données "Bibliothèque en ligne"
-- Utilisé à l'identique par la version monolithique (avant migration)
-- et par la version microservices (après migration), afin de garantir
-- une comparaison équitable entre les deux architectures.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100) NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    total_copies INT DEFAULT 1,
    available_copies INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    book_id INT REFERENCES books(id),
    loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    return_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'en_cours'
);

-- Utilisée uniquement par la version microservices : auth-service émet un
-- jeton à la connexion, que les autres services vérifient auprès de lui
-- avant chaque action (communication inter-services).
CREATE TABLE IF NOT EXISTS tokens (
    token VARCHAR(36) PRIMARY KEY,
    user_id INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Données d'exemple pour pouvoir tester immédiatement
INSERT INTO books (title, author, isbn, total_copies, available_copies) VALUES
('Le Petit Prince', 'Antoine de Saint-Exupéry', '9782070408504', 3, 3),
('1984', 'George Orwell', '9782070368228', 2, 2),
('Réseaux et Télécoms', 'Claude Servin', '9782100747657', 4, 4),
('Sécurité Informatique - Principes et Méthodes', 'Solange Ghernaouti', '9782744077605', 2, 2),
('Introduction à Docker et aux Conteneurs', 'Collectif', '9782409012345', 3, 3)
ON CONFLICT (isbn) DO NOTHING;
