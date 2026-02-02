"""
Tests for the High School Management System API.
"""

import pytest
from fastapi import status


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint."""
    
    def test_get_activities_success(self, client):
        """Test getting all activities."""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # Should have 9 activities
        
        # Check that Basketball Team exists with expected structure
        assert "Basketball Team" in data
        basketball = data["Basketball Team"]
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
        assert isinstance(basketball["participants"], list)
        
    def test_activities_have_required_fields(self, client):
        """Test that all activities have required fields."""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"{activity_name} missing {field}"


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity."""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Basketball Team" in data["message"]
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Basketball Team"]["participants"]
    
    def test_signup_duplicate_student(self, client):
        """Test that signing up the same student twice fails."""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Basketball%20Team/signup?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second signup should fail
        response2 = client.post(f"/activities/Basketball%20Team/signup?email={email}")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity."""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_increases_participant_count(self, client):
        """Test that signup increases the participant count."""
        # Get initial count
        activities_response = client.get("/activities")
        initial_count = len(activities_response.json()["Chess Club"]["participants"])
        
        # Sign up new student
        client.post("/activities/Chess%20Club/signup?email=newchess@mergington.edu")
        
        # Check new count
        activities_response = client.get("/activities")
        new_count = len(activities_response.json()["Chess Club"]["participants"])
        
        assert new_count == initial_count + 1


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint."""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity."""
        # First, ensure the student is registered
        email = "james@mergington.edu"
        
        # Verify student is in Basketball Team
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Basketball Team"]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/Basketball%20Team/unregister?email={email}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        assert email not in activities_response.json()["Basketball Team"]["participants"]
    
    def test_unregister_not_registered_student(self, client):
        """Test unregistering a student who is not registered."""
        response = client.delete(
            "/activities/Basketball%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity."""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_decreases_participant_count(self, client):
        """Test that unregister decreases the participant count."""
        # Get initial count
        activities_response = client.get("/activities")
        initial_count = len(activities_response.json()["Drama Club"]["participants"])
        
        # Unregister existing student
        client.delete("/activities/Drama%20Club/unregister?email=emily@mergington.edu")
        
        # Check new count
        activities_response = client.get("/activities")
        new_count = len(activities_response.json()["Drama Club"]["participants"])
        
        assert new_count == initial_count - 1


class TestIntegrationScenarios:
    """Integration tests for common user workflows."""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test the complete workflow of signing up and unregistering."""
        email = "workflow@mergington.edu"
        activity = "Swimming Club"
        
        # 1. Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == status.HTTP_200_OK
        
        # 2. Verify student is in the activity
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
        
        # 3. Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # 4. Verify student is no longer in the activity
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity]["participants"]
    
    def test_multiple_students_signup(self, client):
        """Test multiple students signing up for the same activity."""
        activity = "Art Studio"
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(
                f"/activities/{activity.replace(' ', '%20')}/signup?email={student}"
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify all students are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity]["participants"]
        
        for student in students:
            assert student in participants
