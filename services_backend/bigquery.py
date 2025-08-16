import os
from google.cloud import bigquery 

if os.environ.get('HACKATHON_BIGQUERY_KEY') is not None:
   GOOGLE_APPLICATION_CREDENTIALS = os.getenv('HACKATHON_BIGQUERY_KEY')

bigquery_client = bigquery.Client(project='formlabs-data-prod')


def run_recent_jobs_query(printer_serial):
    """
    Run a query to get recent jobs for a specific printer serial
    Returns a tuple: (full_results, job_names_string)
    """
    recent_jobs_query = f"""
    SELECT pr.printer_serial, pr.print_guid, j.name, pr.print_started_at
    FROM form4_logs.print AS pr
    INNER JOIN form4_logs.job AS j 
    ON pr.printer_serial = j.printer_serial
    AND pr.job_guid = j.job_guid
    WHERE pr.printer_serial = '{printer_serial}'
    ORDER BY print_started_at DESC
    LIMIT 5
    """
    
    try:
        query_job = bigquery_client.query(recent_jobs_query)
        results = query_job.result()
        full_results = [dict(row) for row in results]
        
        # Extract job names and concatenate them with newlines
        job_names = [row['name'] for row in full_results if row.get('name')]
        job_names_string = "\n".join(job_names) if job_names else "No jobs found"
        
        return full_results, job_names_string
    except Exception as e:
        print(f"Error running query: {e}")
        return [], "Error retrieving jobs"


def run_custom_query(query_string):
    """
    Run a custom BigQuery query
    """
    try:
        query_job = bigquery_client.query(query_string)
        results = query_job.result()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"Error running query: {e}")
        return []


# Example usage:
if __name__ == "__main__":
    # Example: Get recent jobs for a printer
    printer_serial = "Form4-BaroqueTurtle"
    recent_jobs = run_recent_jobs_query(printer_serial)
    print("Recent jobs:", recent_jobs)