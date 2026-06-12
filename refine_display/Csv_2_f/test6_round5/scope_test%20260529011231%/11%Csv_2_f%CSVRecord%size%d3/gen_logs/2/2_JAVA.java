package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_2Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_nonEmptyArray() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(1, record.size());
    }

    @Test
    public void testSize_withNullValues() throws Exception {
        String[] values = {null, null, null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 0);
        Assertions.assertEquals(1000, record.size());
    }
}