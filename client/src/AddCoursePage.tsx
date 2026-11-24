import {useState} from 'react'
import React from 'react'

const loadCourses= async()=>{
    try{
        const res = await fetch('/api/courses/search_courses');
        let courses = await res.json;
        
        
    }catch(err){
        console.error(err);
    }

}


export default function AddCourse() {
    const [subject,setSubject] = useState('');
    const [course_number,setCourse_Number] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSearch(){
        try{
            const res = await fetch('/api/courses/search_courses',{
                method: 'GET',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: new URLSearchParams({ subject, course_number }).toString()
            }
            );
            if(res.ok){
                let subject_name = subject.toString() 
                let course_num = course_number.toString()
                displayCourse(subject_name,course_num)
            }

            // error 401: invalid course id
            if (res.status === 401) {
                setError('Invalid Course ID');
            } else{
                setError('Could not find course id');
            }
        }catch{
            setError('Could not reach the server.');
        }
    }
    function displayCourse(subject_name:string, course_num:string){
        <h1> Add {subject_name} {course_num} ?
            <button className="secondary-button" type="submit">Add Course</button>
        </h1>
        
    }
    
    return(
    <main> className="auth-card"
      <p className="eyebrow">CPS420</p>
      <h1>Add Course</h1>
      <p className="auth-description">Add a course to your profile.</p>
        <form className="AddCourse" >
            <label className="form-field"> Subject
                
                    <input
                        placeholder="Search class subject (ex. CPS)"
                        value={subject}
                        type="subject"
                        onChange={(e) => setSubject(e.target.value)}

                    ></input>
            </label>

            <label className="form-field">Course Number
                    
                    <input
                        placeholder="Search course number"
                        value={course_number}
                        type="course_number"
                        onChange={(e) => setCourse_Number(e.target.value)}
                        
                    
                    ></input>
                    </label>
                
            
        </form>
        </main>
        
    )
}





