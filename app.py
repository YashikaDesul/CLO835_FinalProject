from flask import Flask, render_template, request
import os
import boto3
import logging
import mysql.connector
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Flask
app = Flask(__name__)

# MySQL credentials from environment variables (Kubernetes secrets)
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql-service')
MYSQL_DB = os.getenv('MYSQL_DB', 'mydb')

# MySQL Connection Helper
def get_db_connection():
    return mysql.connector.connect(
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        host=MYSQL_HOST,
        database=MYSQL_DB
    )

# S3 Bucket configuration
s3_client = boto3.client('s3')
#BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'my-clo835-backgrounds')
BUCKET_NAME = os.getenv('S3_BUCKET', 'my-clo835-backgrounds')

# Download background image from S3
def download_background_image():
    local_path = '/tmp/background.jpg'
    static_path = os.path.join(app.static_folder, 'background.jpg')
    try:
        s3_client.download_file(BUCKET_NAME, 'background.jpg', local_path)
        logger.info(f"Downloaded background image from s3://{BUCKET_NAME}/background.jpg")
        shutil.copy(local_path, static_path)
        logger.info(f"Copied background image to {static_path}")
        return '/static/background.jpg'
    except Exception as e:
        logger.warning(f"Could not download image from S3. Reason: {e}")
        return '/static/default-image.jpg' if os.path.exists(static_path) else ''

# Call this on app startup
BACKGROUND_IMAGE_LOCAL = download_background_image()

# Group Name and Slogan from ConfigMap (env variables)
GROUP_NAME = os.getenv('GROUP_NAME', 'Group-13')
GROUP_SLOGAN = os.getenv('GROUP_SLOGAN', 'Scaling the Future')

# Routes
@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('addemp.html',
                          background_image=BACKGROUND_IMAGE_LOCAL,
                          group_name=GROUP_NAME,
                          group_slogan=GROUP_SLOGAN)

@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('about.html',
                          background_image=BACKGROUND_IMAGE_LOCAL,
                          group_name=GROUP_NAME,
                          group_slogan=GROUP_SLOGAN)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        conn.commit()
        emp_name = first_name + " " + last_name
    except Exception as e:
        logger.error(f"Failed to insert employee: {e}")
        return f"Error: {e}"
    finally:
        cursor.close()
        conn.close()

    return render_template('addempoutput.html',
                          name=emp_name,
                          background_image=BACKGROUND_IMAGE_LOCAL,
                          group_name=GROUP_NAME,
                          group_slogan=GROUP_SLOGAN)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template("getemp.html",
                          background_image=BACKGROUND_IMAGE_LOCAL,
                          group_name=GROUP_NAME,
                          group_slogan=GROUP_SLOGAN)

@app.route("/fetchdata", methods=['GET', 'POST'])
def FetchData():
    emp_id = request.form['emp_id']
    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location FROM employee WHERE emp_id=%s"
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        if result:
            output["emp_id"] = result[0]
            output["first_name"] = result[1]
            output["last_name"] = result[2]
            output["primary_skills"] = result[3]
            output["location"] = result[4]
        else:
            return "No employee found with ID: " + emp_id
    except Exception as e:
        logger.error(f"Error retrieving data: {e}")
        return f"Error: {e}"
    finally:
        cursor.close()
        conn.close()

    return render_template("getempoutput.html",
                          id=output["emp_id"],
                          fname=output["first_name"],
                          lname=output["last_name"],
                          interest=output["primary_skills"],
                          location=output["location"],
                          background_image=BACKGROUND_IMAGE_LOCAL,
                          group_name=GROUP_NAME,
                          group_slogan=GROUP_SLOGAN)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
