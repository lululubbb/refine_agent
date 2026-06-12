package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_3Test {

    @Test
    public void testIsConsistent_mappingIsNull() {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsConsistent_mappingSizeEqualsValuesLength() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent());
    }

    @Test
    public void testIsConsistent_emptyValuesAndNullMapping() {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsConsistent_emptyValuesAndEmptyMapping() {
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsConsistent_nullValuesAndNullMapping() {
        CSVRecord record = new CSVRecord(null, null, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    public void testIsConsistent_nullValuesAndNonEmptyMapping() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        CSVRecord record = new CSVRecord(null, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent());
    }
}