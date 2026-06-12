package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_2Test {

    @Test
    public void testisConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testisConsistent_mappingSizeMatchesValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testisConsistent_mappingSizeDoesNotMatchValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent());
    }

    @Test
    public void testisConsistent_emptyValuesAndMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testisConsistent_emptyValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertEquals(true, record.isConsistent());
    }

    @Test
    public void testisConsistent_nonEmptyValuesAndEmptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertEquals(false, record.isConsistent());
    }
}