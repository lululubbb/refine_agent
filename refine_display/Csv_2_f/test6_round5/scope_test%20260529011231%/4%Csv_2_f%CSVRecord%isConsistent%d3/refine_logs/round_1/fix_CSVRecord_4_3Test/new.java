package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_3Test {

    @Test
    public void testIsConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to be true when mapping is null.");
    }

    @Test
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to be true when mapping size equals values length.");
    }

    @Test
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to be false when mapping size does not equal values length.");
    }

    @Test
    public void testIsConsistent_emptyValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to be true for empty values and null mapping.");
    }

    @Test
    public void testIsConsistent_emptyValuesAndEmptyMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to be true for empty values and empty mapping.");
    }

    @Test
    public void testIsConsistent_nullValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(null, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected isConsistent to be true for null values and null mapping.");
    }

    @Test
    public void testIsConsistent_nullValuesAndNonEmptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        CSVRecord record = new CSVRecord(null, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected isConsistent to be false for null values and non-empty mapping.");
    }
}