import { useEffect, useState } from "react";
export interface UserCourseItem {
  id: number;
  course_id: number;
  subject: string;
  course_number: string;
  created_at: string; 
}

 export default function UserCourseList() {
  const [courses, setCourses] = useState<UserCourseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const response = await fetch("/api/user-courses", {
                 });

        if (response.ok) {
           const data: UserCourseItem[] = await response.json();
           setCourses(data);
           setSuccess("Courses retrieved")
        }else{
            setError("Cannot get data")
        }      
        
      } catch {
        setError("Could not connect to server");
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  } );


  return (
    <main className="auth-card">
          
        <table>
        <thead>
            <tr>
            <th>Your Courses</th>
            <th></th>
            </tr>
        </thead>
        <tbody>
            {courses.map((item) => (
            <tr key={item.id}>
                <td>{item.subject} {item.course_number}</td>
            </tr>
            ))}
        </tbody>
        </table>
        {success && <p className="form-message form-message--success" role="status">{success}</p>}
        {error && <p className="form-message form-message--error" role="alert">{error}</p>}
    </main>
  );
}
