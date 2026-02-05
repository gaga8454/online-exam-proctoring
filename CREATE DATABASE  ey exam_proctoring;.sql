CREATE DATABASE exam_proctoring;

CREATE USER 'exam_user'@'localhost' IDENTIFIED BY 'exam123';

GRANT ALL PRIVILEGES ON exam_proctoring.* TO 'exam_user'@'localhost';

FLUSH PRIVILEGES;