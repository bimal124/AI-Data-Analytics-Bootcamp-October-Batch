CREATE TABLE movies(
movie_id SERIAL primary key,
title VARCHAR(100) NOT NULL,
release_year INT,
genre VARCHAR(50)
);

SELECT * FROM movies

CREATE TABLE movie_cast(
movie_id INT REFERENCES movies(movie_id),
actor_id INT REFERENCES actors(actor_id),
role VARCHAR(100),
PRIMARY KEY(movie_id,actor_id)
)


SELECT * FROM movies

CREATE TABLE directors (
 director_id SERIAL PRIMARY KEY,
 first_name VARCHAR(50),
 last_name VARCHAR(50),
 birthdate DATE
);

CREATE TABLE movie_directors (
 movie_id INT REFERENCES movies(movie_id),
 director_id INT REFERENCES directors(director_id),
 PRIMARY KEY (movie_id, director_id)
);

INSERT INTO movies (title, release_year, genre) 
VALUES  ('Inception', 2010, 'Sci-Fi'), 
		('The Dark Knight', 2008, 'Action'), 
		('The Matrix', 1999, 'Action');

INSERT INTO movies (title, release_year, genre) 
VALUES ('tempesto', 2001, 'Sci-Fi');

SELECT * FROM movies






















