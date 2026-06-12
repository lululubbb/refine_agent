package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_7_4Test {

    @Test
    public void testIterator_withValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_emptyValues() throws Exception {
        String[] values = {};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_singleValue() throws Exception {
        String[] values = {"singleValue"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withNullValues() throws Exception {
        String[] values = {null, "value2", null};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withEmptyStrings() throws Exception {
        String[] values = {"", "value2", ""};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withMixedValues() throws Exception {
        String[] values = {null, "", "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withBoundaryValues() throws Exception {
        String[] values = {"value1", "", null, "value4", "value5"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value4", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value5", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}