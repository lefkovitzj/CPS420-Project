import {Component, useState} from 'react'
import { stringify } from 'vitest/internal/browser';


export default function AddCourse() {
    const [subject,setSubject] = useState('');
    const [course_number,setCourse_Number] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSubmit(e: React.FormEvent){
        e.preventDefault();
        setSuccess('');
        setError('');
       try{
            const response = await fetch('/api/profile/courses',{ //url is incorrect; fix here
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({subject:subject, course_number:course_number}),
            }
            );

            if(response.ok){
               setSuccess('Course added!');
               return ;
            }
            
            // error 401: invalid course id
            if (response.status === 401) {
                setError('Invalid Course ID');
            } else{
                setError('Adding course faile');
            }
          
        }catch{
          setError('Could not reach the server.');
        }
    }

    
    return(
    <main className="auth-card">
      <p className="eyebrow">CPS420</p>
      <h1>Add Course</h1>
      <p className="auth-description">Add a course to your profile.</p>
      
        <form className="AddCourse"  onSubmit={handleSubmit}>
            <label className="form-field"> Subject
                
                    <input
                        placeholder="Search class subject (ex. CPS)"
                        value={subject}
                        type="subject"
                        onChange={(e) => setSubject(e.target.value)}
                        required

                    ></input>
            </label>

            <label className="form-field">Course Number
                    
                    <input
                        placeholder="Search course number"
                        value={course_number}
                        type="course_number"
                        onChange={(e) => setCourse_Number(e.target.value)}
                        required
                        
                    ></input>
                    </label>

        <button className="secondary-button" type="submit">Add Course</button>
        {error && <p className="form-message form-message--error" role="alert">{error}</p>}
        {success && <p className="form-message form-message--success" role="status">{success}</p>}
      
        </form>

        <p className="auth-footer">
            Check your courses here: <a href="./usercourses">Courselist</a>.
        </p>
        </main>
        
    )
}

