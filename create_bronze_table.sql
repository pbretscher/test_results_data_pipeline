drop table bronze.raw_athlete_test

create table bronze.raw_athlete_test (
	id SERIAL PRIMARY KEY,
	file_name varchar(50) not null,
	sheet varchar(50) not null,
	athlete varchar(50) not null,
	exercise varchar(50) not null,
	side varchar(10) not null,
	pain_location varchar(50),
	pain varchar(50),
	value numeric(10, 4),
	comments varchar(255),
	dwh_b_created timestamptz default current_timestamp
)
