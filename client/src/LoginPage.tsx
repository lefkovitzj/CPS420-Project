//login page for app; code based off code from registration page

import {usestate } from 'react' //importing package

export default function login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

async function login(e: React.FormEvent) {
     e.preventDefault();
    setSuccess('');
    setError('');

    try{
        //error 401: wrong password/wrong login
        const response = await fetch('http://127.0.0.1:5000/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
      });
    if (response.ok) {
        setSuccess('Account logged in.');
        return;
    }


}