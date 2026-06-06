from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from garden.models import Plant

from .models import PlantSoil, PlantSoilComponent, SoilComponent


class PlantSoilViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='soil-user', password='password')
        self.plant = Plant.objects.create(
            user=self.user,
            name='Монстера',
            watering_interval_days=7,
            last_watered_at=timezone.now(),
        )
        self.ground = SoilComponent.objects.create(user=self.user, name='Грунт')
        self.perlite = SoilComponent.objects.create(user=self.user, name='Перлит')
        self.client.force_login(self.user)

    def test_create_plant_soil_marks_it_current(self):
        response = self.client.post(
            reverse('soil:plant_soil_create', kwargs={'plant_pk': self.plant.pk}),
            {
                'name': 'После пересадки',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '4',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '30',
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '70',
            },
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        plant_soil = PlantSoil.objects.get(plant=self.plant)
        self.assertTrue(plant_soil.is_current)
        self.assertEqual(plant_soil.parts.count(), 2)

    def test_replace_plant_soil_keeps_old_soil_in_history(self):
        old_soil = PlantSoil.objects.create(plant=self.plant, user=self.user, is_current=True)
        PlantSoilComponent.objects.create(
            plant_soil=old_soil,
            soil_component=self.ground,
            percentage='100',
        )

        response = self.client.post(
            reverse('soil:plant_soil_replace', kwargs={'pk': old_soil.pk}),
            {
                'name': 'Новый состав',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '4',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '30',
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '70',
            },
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        old_soil.refresh_from_db()
        new_soil = PlantSoil.objects.get(plant=self.plant, is_current=True)
        self.assertFalse(old_soil.is_current)
        self.assertNotEqual(old_soil.pk, new_soil.pk)

    def test_component_percentages_must_sum_to_100(self):
        response = self.client.post(
            reverse('soil:plant_soil_create', kwargs={'plant_pk': self.plant.pk}),
            {
                'name': '',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '4',
                'parts-INITIAL_FORMS': '0',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '30',
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '60',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сумма процентов должна быть ровно 100%')
        self.assertFalse(PlantSoil.objects.exists())

    def test_composition_text_removes_only_decimal_trailing_zeroes(self):
        black_soil = SoilComponent.objects.create(user=self.user, name='Чернозем')
        plant_soil = PlantSoil.objects.create(plant=self.plant, user=self.user, is_current=True)
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='20.00',
        )
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='30.00',
        )
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=black_soil,
            percentage='50.00',
        )

        self.assertEqual(plant_soil.composition_text, '20% Грунт, 30% Перлит, 50% Чернозем')

    def test_edit_form_shows_only_existing_component_rows(self):
        plant_soil = PlantSoil.objects.create(plant=self.plant, user=self.user, is_current=True)
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='40',
        )
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='60',
        )

        response = self.client.get(reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['formset'].forms), 2)

    def test_create_and_replace_forms_start_with_one_empty_component_row(self):
        plant_soil = PlantSoil.objects.create(plant=self.plant, user=self.user, is_current=True)
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='100',
        )

        create_response = self.client.get(reverse('soil:plant_soil_create', kwargs={'plant_pk': self.plant.pk}))
        replace_response = self.client.get(reverse('soil:plant_soil_replace', kwargs={'pk': plant_soil.pk}))

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(len(create_response.context['formset'].forms), 1)
        self.assertEqual(len(replace_response.context['formset'].forms), 1)

    def test_empty_form_uses_current_user_components(self):
        other_user = get_user_model().objects.create_user(username='other-user', password='password')
        SoilComponent.objects.create(user=other_user, name='Чужой компонент')
        plant_soil = PlantSoil.objects.create(plant=self.plant, user=self.user, is_current=True)
        PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='100',
        )

        response = self.client.get(reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}))

        component_names = list(
            response.context['formset'].empty_form.fields['soil_component'].queryset.values_list('name', flat=True),
        )
        self.assertEqual(component_names, ['Грунт', 'Перлит'])

    def test_edit_form_deletes_removed_component_on_save(self):
        black_soil = SoilComponent.objects.create(user=self.user, name='Чернозем')
        plant_soil = PlantSoil.objects.create(
            plant=self.plant,
            user=self.user,
            name='Состав 1',
            is_current=True,
        )
        ground_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='20',
        )
        perlite_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='30',
        )
        black_soil_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=black_soil,
            percentage='50',
        )

        response = self.client.post(
            reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}),
            {
                'name': 'Состав 1',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '3',
                'parts-INITIAL_FORMS': '3',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-id': str(ground_part.pk),
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '20',
                'parts-0-DELETE': 'on',
                'parts-1-id': str(perlite_part.pk),
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '40',
                'parts-2-id': str(black_soil_part.pk),
                'parts-2-soil_component': str(black_soil.pk),
                'parts-2-percentage': '60',
            },
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        self.assertFalse(PlantSoilComponent.objects.filter(pk=ground_part.pk).exists())
        self.assertEqual(plant_soil.parts.count(), 2)
        perlite_part.refresh_from_db()
        black_soil_part.refresh_from_db()
        self.assertEqual(perlite_part.percentage, 40)
        self.assertEqual(black_soil_part.percentage, 60)

    def test_edit_form_rejects_duplicate_components(self):
        plant_soil = PlantSoil.objects.create(
            plant=self.plant,
            user=self.user,
            name='Состав 1',
            is_current=True,
        )
        ground_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='60',
        )
        perlite_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='40',
        )

        response = self.client.post(
            reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}),
            {
                'name': 'Состав 1',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '3',
                'parts-INITIAL_FORMS': '2',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-id': str(ground_part.pk),
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '60',
                'parts-1-id': str(perlite_part.pk),
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '40',
                'parts-2-soil_component': str(self.perlite.pk),
                'parts-2-percentage': '20',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Один компонент нельзя добавить в состав дважды.')
        ground_part.refresh_from_db()
        perlite_part.refresh_from_db()
        self.assertEqual(ground_part.percentage, 60)
        self.assertEqual(perlite_part.percentage, 40)
        self.assertEqual(plant_soil.parts.count(), 2)

    def test_edit_form_ignores_deleted_extra_component_when_validating_total(self):
        plant_soil = PlantSoil.objects.create(
            plant=self.plant,
            user=self.user,
            name='Состав 1',
            is_current=True,
        )
        ground_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='60',
        )
        perlite_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='40',
        )

        response = self.client.post(
            reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}),
            {
                'name': 'Состав 1',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '3',
                'parts-INITIAL_FORMS': '2',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-id': str(ground_part.pk),
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '50',
                'parts-1-id': str(perlite_part.pk),
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '50',
                'parts-2-soil_component': str(self.perlite.pk),
                'parts-2-percentage': '30',
                'parts-2-DELETE': 'on',
            },
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        ground_part.refresh_from_db()
        perlite_part.refresh_from_db()
        self.assertEqual(ground_part.percentage, 50)
        self.assertEqual(perlite_part.percentage, 50)
        self.assertEqual(plant_soil.parts.count(), 2)

    def test_edit_form_rejects_existing_components_total_over_100(self):
        black_soil = SoilComponent.objects.create(user=self.user, name='Чернозем')
        plant_soil = PlantSoil.objects.create(
            plant=self.plant,
            user=self.user,
            name='Состав 1',
            is_current=True,
        )
        ground_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='50',
        )
        perlite_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='30',
        )
        black_soil_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=black_soil,
            percentage='20',
        )

        response = self.client.post(
            reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}),
            {
                'name': 'Состав 1',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '3',
                'parts-INITIAL_FORMS': '3',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-id': str(ground_part.pk),
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '70',
                'parts-1-id': str(perlite_part.pk),
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '30',
                'parts-2-id': str(black_soil_part.pk),
                'parts-2-soil_component': str(black_soil.pk),
                'parts-2-percentage': '40',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сумма процентов должна быть ровно 100%')
        ground_part.refresh_from_db()
        perlite_part.refresh_from_db()
        black_soil_part.refresh_from_db()
        self.assertEqual(ground_part.percentage, 50)
        self.assertEqual(perlite_part.percentage, 30)
        self.assertEqual(black_soil_part.percentage, 20)

    def test_edit_form_deletes_existing_component_while_updating_remaining_total(self):
        black_soil = SoilComponent.objects.create(user=self.user, name='Чернозем')
        plant_soil = PlantSoil.objects.create(
            plant=self.plant,
            user=self.user,
            name='Состав 1',
            is_current=True,
        )
        ground_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.ground,
            percentage='70',
        )
        perlite_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=self.perlite,
            percentage='20',
        )
        black_soil_part = PlantSoilComponent.objects.create(
            plant_soil=plant_soil,
            soil_component=black_soil,
            percentage='10',
        )

        response = self.client.post(
            reverse('soil:plant_soil_edit', kwargs={'pk': plant_soil.pk}),
            {
                'name': 'Состав 1',
                'set_on': timezone.localdate().isoformat(),
                'comment': '',
                'parts-TOTAL_FORMS': '3',
                'parts-INITIAL_FORMS': '3',
                'parts-MIN_NUM_FORMS': '0',
                'parts-MAX_NUM_FORMS': '1000',
                'parts-0-id': str(ground_part.pk),
                'parts-0-soil_component': str(self.ground.pk),
                'parts-0-percentage': '70',
                'parts-1-id': str(perlite_part.pk),
                'parts-1-soil_component': str(self.perlite.pk),
                'parts-1-percentage': '30',
                'parts-2-id': str(black_soil_part.pk),
                'parts-2-DELETE': 'on',
            },
        )

        self.assertRedirects(response, reverse('garden:plant_detail', kwargs={'pk': self.plant.pk}))
        self.assertFalse(PlantSoilComponent.objects.filter(pk=black_soil_part.pk).exists())
        ground_part.refresh_from_db()
        perlite_part.refresh_from_db()
        self.assertEqual(ground_part.percentage, 70)
        self.assertEqual(perlite_part.percentage, 30)
        self.assertEqual(plant_soil.parts.count(), 2)
