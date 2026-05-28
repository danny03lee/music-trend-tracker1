# Requirements Document

## Introduction

The Spotify Global Trend Tracker is an automated ETL pipeline that extracts weekly Spotify chart data, audio features, and artist metadata across multiple regions, transforms and stores the data historically in SQLite, backs up to S3, and presents interactive trend visualizations through a Streamlit dashboard. The pipeline runs on a weekly schedule via GitHub Actions.

## Glossary

- **Pipeline**: The end-to-end automated workflow consisting of the Extract, Transform, and Load stages executed in sequence
- **Extractor**: The module responsible for pulling raw data from the Spotify API via Spotipy
- **Transformer**: The module responsible for normalizing, joining, and enriching raw extracted data into a consistent schema
- **Loader**: The module responsible for writing transformed data to SQLite and backing up the database to S3
- **Dashboard**: The Streamlit-based web application that visualizes trend data from the SQLite database
- **Scheduler**: The GitHub Actions workflow that triggers the Pipeline on a weekly cadence
- **Region**: A Spotify market identifier representing a geographic area (e.g., Global, US, UK, Japan, Brazil)
- **Audio_Features**: A set of Spotify-provided numeric attributes for a track including energy, tempo, danceability, valence, and acousticness
- **Chart_Entry**: A single record representing a track's rank in a specific Region for a given week
- **Track_Status**: A classification assigned to a Chart_Entry indicating whether the track is a new entry, a rising track, or a returning track relative to the previous week
- **Week_Timestamp**: An ISO 8601 date string representing the Monday of the week in which data was collected
- **SQLite_Database**: The local relational database file used for persistent historical storage of all Pipeline data
- **S3_Backup**: A copy of the SQLite_Database uploaded to an Amazon S3 bucket after each Pipeline run using boto3

## Requirements

### Requirement 1: Extract Weekly Chart Data

**User Story:** As a data analyst, I want the Pipeline to pull weekly top chart data from Spotify for multiple regions, so that I can compare chart performance across markets.

#### Acceptance Criteria

1. WHEN the Extractor is triggered, THE Extractor SHALL retrieve the top 50 chart tracks for each of the following Regions: Global, US, UK, Japan, and Brazil
2. WHEN the Extractor retrieves chart data, THE Extractor SHALL capture the track identifier, track name, artist identifier, and rank for each Chart_Entry
3. IF the Spotify API returns an error during chart extraction, THEN THE Extractor SHALL log the error with the Region name and the HTTP status code and halt the Pipeline

### Requirement 2: Extract Audio Features

**User Story:** As a data analyst, I want audio features extracted for every charting track, so that I can analyze what makes songs go viral.

#### Acceptance Criteria

1. WHEN the Extractor has retrieved chart data, THE Extractor SHALL retrieve Audio_Features for every unique track identifier present in the chart data
2. WHEN the Extractor retrieves Audio_Features, THE Extractor SHALL capture energy, tempo, danceability, valence, acousticness, and popularity for each track
3. IF the Spotify API returns an error for a specific track's Audio_Features request, THEN THE Extractor SHALL log the track identifier and the error, skip that track, and continue processing remaining tracks

### Requirement 3: Extract Artist Metadata

**User Story:** As a data analyst, I want artist metadata extracted for every charting artist, so that I can track artist popularity over time.

#### Acceptance Criteria

1. WHEN the Extractor has retrieved chart data, THE Extractor SHALL retrieve metadata for every unique artist identifier present in the chart data
2. WHEN the Extractor retrieves artist metadata, THE Extractor SHALL capture the artist name, genres, follower count, and popularity score
3. IF the Spotify API returns an error for a specific artist metadata request, THEN THE Extractor SHALL log the artist identifier and the error, skip that artist, and continue processing remaining artists

### Requirement 4: Transform and Normalize Chart Data

**User Story:** As a data analyst, I want chart data normalized into a consistent schema, so that cross-region comparisons are reliable.

#### Acceptance Criteria

1. WHEN the Transformer receives raw chart data, THE Transformer SHALL normalize all Chart_Entry records into a single schema containing week, region, rank, track_id, track_name, and artist_id columns
2. WHEN the Transformer normalizes chart data, THE Transformer SHALL assign the current Week_Timestamp to every record
3. THE Transformer SHALL produce identical column names and data types for Chart_Entry records regardless of the source Region

### Requirement 5: Join Tracks with Audio Features and Artist Metadata

**User Story:** As a data analyst, I want chart data enriched with audio features and artist metadata, so that I can perform combined analysis.

#### Acceptance Criteria

1. WHEN the Transformer has normalized chart data, THE Transformer SHALL join each Chart_Entry with its corresponding Audio_Features record using the track identifier
2. WHEN the Transformer has normalized chart data, THE Transformer SHALL join each Chart_Entry with its corresponding artist metadata record using the artist identifier
3. IF a Chart_Entry has no matching Audio_Features record, THEN THE Transformer SHALL retain the Chart_Entry with null values for the Audio_Features columns
4. IF a Chart_Entry has no matching artist metadata record, THEN THE Transformer SHALL retain the Chart_Entry with null values for the artist metadata columns

### Requirement 6: Classify Track Status Week Over Week

**User Story:** As a data analyst, I want tracks classified as new, rising, or returning each week, so that I can identify chart movement patterns.

#### Acceptance Criteria

1. WHEN the Transformer processes Chart_Entry records, THE Transformer SHALL compare each track's presence against the previous week's chart data for the same Region
2. WHEN a track appears in the current week but did not appear in the previous week's chart for the same Region, THE Transformer SHALL assign a Track_Status of "new_entry"
3. WHEN a track appears in the current week at a higher rank than the previous week in the same Region, THE Transformer SHALL assign a Track_Status of "rising"
4. WHEN a track was absent for two or more consecutive weeks and reappears in the current week's chart for the same Region, THE Transformer SHALL assign a Track_Status of "returning"
5. WHEN a track appears in the current week at the same or lower rank than the previous week in the same Region, THE Transformer SHALL assign a Track_Status of "stable_or_falling"

### Requirement 7: Load Data to SQLite

**User Story:** As a data engineer, I want transformed data written to SQLite with weekly partitioning, so that historical records are preserved.

#### Acceptance Criteria

1. WHEN the Loader receives transformed data, THE Loader SHALL write Chart_Entry records to the "charts" table with columns: week, region, rank, track_id, track_name, artist_id
2. WHEN the Loader receives transformed data, THE Loader SHALL write Audio_Features records to the "audio_features" table with columns: track_id, energy, tempo, danceability, valence, acousticness, popularity
3. WHEN the Loader receives transformed data, THE Loader SHALL write artist records to the "artists" table with columns: artist_id, name, genres, followers, popularity
4. THE Loader SHALL append new records to existing tables and SHALL preserve all previously loaded historical records
5. IF the Loader encounters a database write error, THEN THE Loader SHALL roll back the current transaction and log the error

### Requirement 8: Backup SQLite Database to S3

**User Story:** As a data engineer, I want the database backed up to S3 after each run, so that data is protected against local storage failures.

#### Acceptance Criteria

1. WHEN the Loader has completed writing to the SQLite_Database, THE Loader SHALL upload the SQLite_Database file to the configured S3 bucket using boto3
2. WHEN the Loader uploads the S3_Backup, THE Loader SHALL include the Week_Timestamp in the S3 object key to distinguish backups by week
3. IF the S3 upload fails, THEN THE Loader SHALL log the error with the S3 bucket name and the HTTP status code and report the failure without halting the Pipeline

### Requirement 9: Dashboard - Global vs Regional Chart Comparison

**User Story:** As a data analyst, I want to compare which songs appear across multiple regional charts, so that I can identify tracks with cross-market appeal.

#### Acceptance Criteria

1. THE Dashboard SHALL display a view showing tracks that appear in charts for two or more Regions within the same week
2. WHEN a user selects a specific week, THE Dashboard SHALL display the chart rankings of each cross-market track across all Regions where the track appears
3. THE Dashboard SHALL allow the user to filter the comparison view by Region, date range, and genre

### Requirement 10: Dashboard - Audio Feature Breakdown

**User Story:** As a data analyst, I want to see audio feature patterns of top charting songs, so that I can understand what a viral song sounds like.

#### Acceptance Criteria

1. THE Dashboard SHALL display an aggregated view of Audio_Features (energy, tempo, danceability, valence, acousticness) for the top charting tracks in a selected week
2. WHEN a user selects a Region and date range, THE Dashboard SHALL display the average Audio_Features values for the top 50 tracks in that selection
3. THE Dashboard SHALL present Audio_Features data using visual charts suitable for comparing multiple numeric dimensions

### Requirement 11: Dashboard - Artist Popularity Trends

**User Story:** As a data analyst, I want to see artist popularity trend lines over time, so that I can track how artist popularity evolves.

#### Acceptance Criteria

1. WHEN a user selects one or more artists, THE Dashboard SHALL display a time-series line chart of each selected artist's popularity score across all available weeks
2. THE Dashboard SHALL allow the user to search for and select artists by name
3. THE Dashboard SHALL display the follower count alongside the popularity score for each selected artist

### Requirement 12: Dashboard - Rising vs Falling Tracks

**User Story:** As a data analyst, I want to see which tracks are rising and which are falling each week, so that I can spot momentum shifts.

#### Acceptance Criteria

1. WHEN a user selects a week and Region, THE Dashboard SHALL display a list of tracks with their Track_Status classification (new_entry, rising, returning, stable_or_falling)
2. THE Dashboard SHALL sort the rising and falling tracks view by rank change magnitude in descending order
3. THE Dashboard SHALL allow the user to filter the view by Region and date range

### Requirement 13: Dashboard Filtering

**User Story:** As a data analyst, I want to filter dashboard views by region, date range, and genre, so that I can focus my analysis.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a Region filter that allows the user to select one or more Regions from the available set
2. THE Dashboard SHALL provide a date range filter that allows the user to select a start week and end week
3. THE Dashboard SHALL provide a genre filter that allows the user to select one or more genres from the genres present in the artist metadata
4. WHEN the user applies any combination of filters, THE Dashboard SHALL update all visible views to reflect only the filtered data

### Requirement 14: GitHub Actions Weekly Schedule

**User Story:** As a data engineer, I want the Pipeline to run automatically every Monday morning, so that data stays current without manual intervention.

#### Acceptance Criteria

1. THE Scheduler SHALL trigger the Pipeline every Monday at 08:00 UTC
2. WHEN the Scheduler triggers the Pipeline, THE Scheduler SHALL execute the Extractor, Transformer, and Loader stages in sequence
3. THE Scheduler SHALL retrieve Spotify API credentials and AWS credentials from GitHub Secrets
4. IF any stage of the Pipeline fails, THEN THE Scheduler SHALL report the failure in the GitHub Actions run log and stop execution of subsequent stages

### Requirement 15: Configuration Management

**User Story:** As a developer, I want all configurable values centralized in a configuration module, so that I can adjust settings without modifying pipeline code.

#### Acceptance Criteria

1. THE Pipeline SHALL read the Spotify API client ID, client secret, S3 bucket name, S3 key prefix, and the list of target Regions from a centralized configuration module
2. THE Pipeline SHALL support overriding configuration values via environment variables
3. IF a required configuration value is missing, THEN THE Pipeline SHALL raise a descriptive error identifying the missing value and halt execution
