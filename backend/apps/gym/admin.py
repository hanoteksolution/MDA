from django.contrib import admin

from apps.gym.models import (
    Attendance,
    BodyMeasurement,
    ClassBooking,
    ClassSchedule,
    Exercise,
    GymClass,
    Member,
    MemberTrainerAssignment,
    MemberWorkoutAssignment,
    MembershipPlan,
    MembershipSubscription,
    PersonalTrainingSession,
    Trainer,
    TrainerSchedule,
    TrainerSpecialty,
    WorkoutDay,
    WorkoutExercise,
    WorkoutPlan,
    WorkoutProgress,
    WorkoutProgressSet,
)

admin.site.register(Member)
admin.site.register(MembershipPlan)
admin.site.register(MembershipSubscription)
admin.site.register(Attendance)
admin.site.register(TrainerSpecialty)
admin.site.register(Trainer)
admin.site.register(TrainerSchedule)
admin.site.register(MemberTrainerAssignment)
admin.site.register(PersonalTrainingSession)
admin.site.register(GymClass)
admin.site.register(ClassSchedule)
admin.site.register(ClassBooking)
admin.site.register(Exercise)
admin.site.register(WorkoutPlan)
admin.site.register(WorkoutDay)
admin.site.register(WorkoutExercise)
admin.site.register(MemberWorkoutAssignment)
admin.site.register(WorkoutProgress)
admin.site.register(WorkoutProgressSet)
admin.site.register(BodyMeasurement)
