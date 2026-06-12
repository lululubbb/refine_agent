package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_2Test {

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 5L;
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord record = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    @Test
    public void testgetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -1L;
        CSVRecord record = createCSVRecord(new String[]{"value1"}, expectedRecordNumber);
        Assertions.assertEquals(expectedRecordNumber, record.getRecordNumber());
    }

    private CSVRecord createCSVRecord(String[] values, long recordNumber) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, recordNumber);
    }
}